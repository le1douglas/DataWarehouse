# bleak needs winrt-runtime on Windows, which has no prebuilt wheel for newer pythons yet
# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["bleak"]
# ///
"""Relay between a OnePen over Bluetooth Low Energy and one TCP client, the backend.

Runs on Windows, where the Bluetooth adapter is (a container cannot reach it):

    uv run src\\bluelab_datastreamer\\ble_bridge.py

Connects to the first ONE- device found and keeps reconnecting. It decodes nothing and decides
nothing: it subscribes, reads and writes only when the backend asks, and forwards the bytes as hex.
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

# what the bytes mean is in edenic_decompiling_result.md, next to this file. the bridge does not
# use any of it: decoding is the backend's job.

import argparse
import asyncio
import json
from datetime import datetime

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic

DEVICE_NAME_FILTER = "ONE-"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SCAN_TIMEOUT_SECONDS = 10
RECONNECT_DELAY_SECONDS = 2

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


async def stream_pen(address: str | None) -> None:
    global pen, pen_line
    while True:
        print("# scanning...", flush=True)
        if address:
            device = await BleakScanner.find_device_by_address(address, timeout=SCAN_TIMEOUT_SECONDS)
        else:
            device = await BleakScanner.find_device_by_filter(
                lambda d, _: d.name is not None and DEVICE_NAME_FILTER in d.name, timeout=SCAN_TIMEOUT_SECONDS
            )
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
    parser.add_argument("--address", help="connect to this device instead of the first ONE- found")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"interface to listen on (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"tcp port (default {DEFAULT_PORT})")
    parser.add_argument("--verbose", action="store_true", help="print every command, result and notification")
    args = parser.parse_args()
    verbose = args.verbose

    server = await asyncio.start_server(serve_backend, args.host, args.port)
    print(f"# listening on {args.host}:{args.port}", flush=True)
    async with server:
        await stream_pen(args.address)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
