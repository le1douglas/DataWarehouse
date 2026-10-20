# bleak needs winrt-runtime on Windows, which has no prebuilt wheel for newer pythons yet
# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["bleak"]
# ///
"""Relay between a OnePen over Bluetooth Low Energy and one TCP client, the backend.

Runs on Windows, where the Bluetooth adapter is (a container cannot reach it):

    uv run src\\bluelab_datastreamer\\ble_bridge.py

At the start it scans and lists the OnePens in range, the devices that advertise the OnePen
service, with the signal strength of each. The one to connect to is chosen with the up and down
arrows and enter, or given with --address, and the bridge keeps reconnecting to that one only.
The backend can connect once a pen is chosen. With --choose it only shows the list, prints the
address chosen and ends, so a script can choose first and start the bridge with --address after
(OnePen.cmd on the desktop does). It decodes nothing and decides nothing: it
subscribes, reads and writes only when the backend asks, and forwards the bytes as hex.
One JSON object per line in both directions. From a container the bridge is at
host.docker.internal:8765.

The backend sends commands, each answered by a result with the same id:

    {"id": 1, "op": "read", "uuid": ...}                 -> {"type": "result", "id": 1, "hex": ...}
    {"id": 2, "op": "write", "uuid": ..., "hex": ...}    -> {"type": "result", "id": 2}
    {"id": 3, "op": "subscribe", "uuid": ...}            -> {"type": "result", "id": 3}
    {"id": 4, "op": "unsubscribe", "uuid": ...}          -> {"type": "result", "id": 4}

A failed command gets {"type": "result", "id": ..., "error": ...}. The bridge also sends:

    {"type": "connected", "time": ..., "name": ..., "address": ..., "mtu": ..., "characteristics": [...]}
    {"type": "notify", "time": ..., "uuid": ..., "hex": ...}
    {"type": "disconnected", "time": ...}

A backend that connects while the pen is connected first gets the connected line. Subscriptions
end when the pen disconnects (the backend subscribes again after the next connected line) and
when the backend disconnects, so the pen sends nothing while no backend listens. Only one backend
at a time: a second connection gets an error line and is closed.
"""

# what the bytes mean is in edenic_decompiling_result.md, next to this file. the bridge uses only
# the service a pen advertises, to find it: decoding is the backend's job.

import argparse
import asyncio
import json
import msvcrt
import os
import shutil
import sys
from datetime import datetime

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# a device is a OnePen when its advertisement lists this service, as in the edenic app
ONEPEN_SERVICE = "983dd3da-d46f-bc05-0100-00c278b6b50a"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SCAN_TIMEOUT_SECONDS = 10
RECONNECT_DELAY_SECONDS = 2
KEY_POLL_SECONDS = 0.05
CHOOSE_HINT = "WHICH PEN? UP AND DOWN TO CHOOSE, ENTER TO CONNECT, Q TO QUIT"
NO_PEN_YET = "  no pen found yet, scanning..."
# terminal escape codes, the same as in datastreamer.py. the list is redrawn by moving the cursor
# up over it and clearing the screen from there down
UP = "\x1b[{}A"
CLEAR_DOWN = "\r\x1b[J"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
YELLOW = "\x1b[33m"
RESET_COLOR = "\x1b[0m"
ENTER = ("\r", "\n")
ARROW_UP = "up"
ARROW_DOWN = "down"
# an arrow key comes as one of these, followed by its code
WINDOWS_KEY_PREFIXES = ("\x00", "\xe0")
WINDOWS_KEYS = {"H": ARROW_UP, "P": ARROW_DOWN}

pen: BleakClient | None = None
# the connected line of the current pen, sent to a backend that connects later
pen_line: dict | None = None
backend: asyncio.StreamWriter | None = None
subscribed: set[str] = set()
verbose = False


def now() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def encode(message: dict) -> bytes:
    return (json.dumps(message) + "\n").encode()


def send(message: dict) -> None:
    # the backend polls several times a second, so commands, results and notifications are only
    # printed with --verbose. the rest is printed short
    if verbose:
        print(json.dumps(message), flush=True)
    elif message["type"] == "connected":
        print(f"# pen {message['name']} {message['address']} connected", flush=True)
    elif message["type"] == "disconnected":
        print("# pen disconnected", flush=True)
    elif "error" in message:
        print(json.dumps(message), flush=True)
    if backend is not None and not backend.is_closing():
        backend.write(encode(message))


def on_notify(char: BleakGATTCharacteristic, payload: bytearray) -> None:
    send({"type": "notify", "time": now(), "uuid": char.uuid, "hex": payload.hex()})


async def run(request: dict) -> dict:
    if pen is None or not pen.is_connected:
        raise RuntimeError("no pen connected")
    op, uuid = request["op"], request["uuid"]
    if op == "read":
        return {"hex": (await pen.read_gatt_char(uuid)).hex()}
    if op == "write":
        await pen.write_gatt_char(uuid, bytes.fromhex(request["hex"]), response=True)
    elif op == "subscribe":
        await pen.start_notify(uuid, on_notify)
        subscribed.add(uuid)
    elif op == "unsubscribe":
        await pen.stop_notify(uuid)
        subscribed.discard(uuid)
    else:
        raise ValueError(f"unknown op {op!r}")
    return {}


async def answer(line: bytes) -> dict:
    request_id = None
    try:
        request = json.loads(line)
        request_id = request.get("id")
        return {"type": "result", "id": request_id, **await run(request)}
    except Exception as error:  # noqa: BLE001
        # a failed command is the backend's to handle, the bridge keeps running
        return {"type": "result", "id": request_id, "error": repr(error)}


async def unsubscribe_all() -> None:
    if pen is not None and pen.is_connected:
        for uuid in list(subscribed):
            try:
                await pen.stop_notify(uuid)
            except Exception as error:  # noqa: BLE001
                print(f"# unsubscribe {uuid} failed: {error!r}", flush=True)
    subscribed.clear()


async def serve_backend(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    global backend
    peer = writer.get_extra_info("peername")
    if backend is not None:
        writer.write(encode({"type": "error", "time": now(), "error": "another backend is connected"}))
        await writer.drain()
        writer.close()
        print(f"# refused backend {peer}, another one is connected", flush=True)
        return

    print(f"# backend connected {peer}", flush=True)
    backend = writer
    if pen_line is not None:
        send(pen_line)
    try:
        async for line in reader:
            if verbose:
                print(f"# command {line.decode().strip()}", flush=True)
            send(await answer(line))
    except ConnectionError:
        pass
    finally:
        backend = None
        # so the pen keeps its saved readings until a backend asks for them
        await unsubscribe_all()
        writer.close()
        print(f"# backend disconnected {peer}", flush=True)


def fit(text: str, yellow: bool) -> str:
    """The line, yellow if marked, cut to the terminal width so it does not wrap and break the redraw."""
    text = text[: shutil.get_terminal_size().columns - 1]
    return f"{YELLOW}{text}{RESET_COLOR}" if yellow else text


def keys_pressed() -> list[str]:
    """The keys pressed since the last call, without waiting. An arrow comes by its name."""
    keys = []
    while msvcrt.kbhit():
        key = msvcrt.getwch()
        if key in WINDOWS_KEY_PREFIXES:
            key = WINDOWS_KEYS.get(msvcrt.getwch())
        if key is not None:
            keys.append(key)
    return keys


async def choose_pen() -> str | None:
    """Lists the pens while scanning, until one is chosen with the arrows and enter. Its address, None on q.

    Draws on stderr, so with --choose only the address is on stdout, for the script that reads it.
    """
    # name and signal strength by address, in the order found, so the list does not reorder under
    # the arrows when the signal changes
    pens: dict[str, tuple[str, int]] = {}

    def on_advertisement(device: BLEDevice, advertisement: AdvertisementData) -> None:
        if ONEPEN_SERVICE not in (uuid.lower() for uuid in advertisement.service_uuids):
            return
        # the name can be missing from an advertisement, then the one seen before is kept
        known_name = pens.get(device.address, ("?", 0))[0]
        pens[device.address] = (advertisement.local_name or device.name or known_name, advertisement.rssi)

    chosen: str | None = None
    shown = ""
    lines = 0
    async with BleakScanner(on_advertisement):
        while True:
            addresses = list(pens)
            if chosen is None and addresses:
                chosen = addresses[0]
            rows = [
                fit(f"> {pen_name}  {address}  {rssi} dBm", address == chosen)
                for address, (pen_name, rssi) in pens.items()
            ] or [NO_PEN_YET]
            text = "".join(f"{row}\n" for row in [fit(CHOOSE_HINT, True), *rows])
            if text != shown:
                print((UP.format(lines) if lines else "") + CLEAR_DOWN + text, end="", file=sys.stderr, flush=True)
                shown, lines = text, len(rows) + 1
            await asyncio.sleep(KEY_POLL_SECONDS)
            for key in keys_pressed():
                if key.lower() == "q":
                    return None
                if chosen is None:
                    continue
                if key in ENTER:
                    print(UP.format(lines) + CLEAR_DOWN, end="", file=sys.stderr, flush=True)
                    print(f"# pen {pens[chosen][0]} {chosen} chosen", file=sys.stderr, flush=True)
                    return chosen
                if key in (ARROW_UP, ARROW_DOWN):
                    index = addresses.index(chosen) + (1 if key == ARROW_DOWN else -1)
                    chosen = addresses[max(0, min(len(addresses) - 1, index))]


async def stream_pen(address: str) -> None:
    global pen, pen_line
    while True:
        print("# scanning...", flush=True)
        device = await BleakScanner.find_device_by_address(address, timeout=SCAN_TIMEOUT_SECONDS)
        if device is None:
            print("# no device found", flush=True)
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            continue

        disconnected = asyncio.Event()
        try:
            async with BleakClient(device, disconnected_callback=lambda _: disconnected.set()) as client:
                pen = client
                pen_line = {
                    "type": "connected",
                    "time": now(),
                    "name": device.name,
                    "address": device.address,
                    "mtu": client.mtu_size,
                    "characteristics": [
                        {"service": service.uuid, "uuid": char.uuid, "properties": char.properties}
                        for service in client.services
                        for char in service.characteristics
                    ],
                }
                send(pen_line)
                await disconnected.wait()
        except Exception as error:  # noqa: BLE001
            # the pen sleeps and advertises again, so every failure is retried
            print(f"# connection failed: {error!r}", flush=True)

        pen = None
        pen_line = None
        subscribed.clear()
        send({"type": "disconnected", "time": now()})
        await asyncio.sleep(RECONNECT_DELAY_SECONDS)


async def main() -> None:
    global verbose
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--address", help="connect to this device instead of choosing one from the list")
    parser.add_argument("--choose", action="store_true", help="only choose a pen from the list, print its address and end")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"interface to listen on (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"tcp port (default {DEFAULT_PORT})")
    parser.add_argument("--verbose", action="store_true", help="print every command, result and notification")
    args = parser.parse_args()
    verbose = args.verbose

    address = args.address
    if address is None:
        # an empty command switches the windows console to understand the escape codes
        os.system("")
        print(HIDE_CURSOR, end="", file=sys.stderr, flush=True)
        try:
            address = await choose_pen()
        finally:
            print(SHOW_CURSOR, end="", file=sys.stderr, flush=True)
        if address is None:
            return
    if args.choose:
        print(address, flush=True)
        return

    # listens only once the pen is chosen, so the lines of a backend do not break the list
    server = await asyncio.start_server(serve_backend, args.host, args.port)
    print(f"# listening on {args.host}:{args.port}", flush=True)
    async with server:
        await stream_pen(address)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
