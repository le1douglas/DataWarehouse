# bleak needs winrt-runtime on Windows, which has no prebuilt wheel for newer pythons yet
# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["bleak"]
# ///
"""Relay between a OnePen over Bluetooth Low Energy and one TCP client, drip_drain_cli.py in a container.

The only part that runs on Windows, where the Bluetooth adapter is (a container cannot reach it),
so it is kept as thin as it can be: it draws nothing and reads no key, and needs no other file of
this folder. OnePen.cmd on the desktop starts it, or by hand:

    uv run src\\bluelab_datastreamer\\onepen_bridge.py

From a container the bridge is at host.docker.internal:8765. It decodes nothing and decides
nothing: it scans, connects, subscribes, reads and writes only when the backend asks, and forwards
the bytes as hex. One JSON object per line in both directions. The backend sends commands, each
answered by a result with the same id:

    {"id": 1, "op": "scan"}                              -> {"type": "result", "id": 1}
    {"id": 2, "op": "connect", "address": ...}           -> {"type": "result", "id": 2}
    {"id": 3, "op": "read", "uuid": ...}                 -> {"type": "result", "id": 3, "hex": ...}
    {"id": 4, "op": "write", "uuid": ..., "hex": ...}    -> {"type": "result", "id": 4}
    {"id": 5, "op": "subscribe", "uuid": ...}            -> {"type": "result", "id": 5}
    {"id": 6, "op": "unsubscribe", "uuid": ...}          -> {"type": "result", "id": 6}

A failed command gets {"type": "result", "id": ..., "error": ...}. The bridge also sends:

    {"type": "advertisement", "time": ..., "address": ..., "name": ..., "rssi": ...}
    {"type": "connected", "time": ..., "name": ..., "address": ..., "mtu": ..., "characteristics": [...]}
    {"type": "notify", "time": ..., "uuid": ..., "hex": ...}
    {"type": "disconnected", "time": ...}
    {"type": "error", "time": ..., "error": ...}

After scan, every advertisement of a OnePen in range is sent, until connect. After connect, the
bridge keeps reconnecting to that address, and sends connected each time; subscriptions end with
every disconnect. When the backend disconnects, the scan stops and the pen is let go, so it keeps
its saved readings until a backend asks for them. Only one backend at a time: a second connection
gets an error line and is closed.
"""

import argparse
import asyncio
import json
from contextlib import suppress
from datetime import datetime

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# a device is a OnePen when its advertisement lists this service, as in the edenic app. the same as
# SERVICE in onepen.py, repeated so this file runs on its own
ONEPEN_SERVICE = "983dd3da-d46f-bc05-0100-00c278b6b50a"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SCAN_TIMEOUT_SECONDS = 10
RECONNECT_DELAY_SECONDS = 2


def now() -> str:
    return datetime.now().isoformat(timespec="microseconds")


def encode(message: dict) -> bytes:
    return (json.dumps(message) + "\n").encode()


async def stop(task: asyncio.Task | None) -> None:
    """Cancels the task and waits until it has ended, so what it holds is let go."""
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


class Console:
    """Prints what the bridge tells. The backend polls several times a second and a pen advertises
    several times a second, so the lines to and from the backend are printed only when verbose."""

    def __init__(self, verbose: bool) -> None:
        self.verbose = verbose

    def event(self, text: str) -> None:
        print(f"# {text}", flush=True)

    def command(self, line: str) -> None:
        if self.verbose:
            print(f"# command {line}", flush=True)

    def sent(self, message: dict) -> None:
        if self.verbose or "error" in message:
            print(json.dumps(message), flush=True)
        elif message["type"] == "connected":
            self.event(f"pen {message['name']} {message['address']} connected")
        elif message["type"] == "disconnected":
            self.event("pen disconnected")


class Bridge:
    """The backend connected, the pen it asked for, and the commands between them. Prints nothing:
    what happens goes to the console."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self.backend: asyncio.StreamWriter | None = None
        self.pen: BleakClient | None = None
        self.subscribed: set[str] = set()
        self._scanner: asyncio.Task | None = None
        self._streamer: asyncio.Task | None = None

    async def serve(self, host: str, port: int) -> None:
        server = await asyncio.start_server(self._serve_backend, host, port)
        self.console.event(f"listening on {host}:{port}")
        async with server:
            await server.serve_forever()

    def _send(self, message: dict) -> None:
        self.console.sent(message)
        if self.backend is not None and not self.backend.is_closing():
            self.backend.write(encode(message))

    def _error(self, text: str) -> None:
        self.console.event(text)
        self._send({"type": "error", "time": now(), "error": text})

    def _on_notify(self, char: BleakGATTCharacteristic, payload: bytearray) -> None:
        self._send({"type": "notify", "time": now(), "uuid": char.uuid, "hex": payload.hex()})

    async def _run(self, request: dict) -> dict:
        op = request["op"]
        if op == "scan":
            if self._scanner is None or self._scanner.done():
                self._scanner = asyncio.create_task(self._scan())
            return {}
        if op == "connect":
            await stop(self._scanner)
            await stop(self._streamer)
            self._streamer = asyncio.create_task(self._stream_pen(request["address"]))
            return {}
        pen, uuid = self.pen, request["uuid"]
        if pen is None or not pen.is_connected:
            raise RuntimeError("no pen connected")
        if op == "read":
            return {"hex": (await pen.read_gatt_char(uuid)).hex()}
        if op == "write":
            await pen.write_gatt_char(uuid, bytes.fromhex(request["hex"]), response=True)
        elif op == "subscribe":
            await pen.start_notify(uuid, self._on_notify)
            self.subscribed.add(uuid)
        elif op == "unsubscribe":
            await pen.stop_notify(uuid)
            self.subscribed.discard(uuid)
        else:
            raise ValueError(f"unknown op {op!r}")
        return {}

    async def _answer(self, line: bytes) -> dict:
        request_id = None
        try:
            request = json.loads(line)
            request_id = request.get("id")
            return {"type": "result", "id": request_id, **await self._run(request)}
        except Exception as error:  # noqa: BLE001
            # a failed command is the backend's to handle, the bridge keeps running
            return {"type": "result", "id": request_id, "error": repr(error)}

    async def _serve_backend(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        if self.backend is not None:
            writer.write(encode({"type": "error", "time": now(), "error": "another backend is connected"}))
            await writer.drain()
            writer.close()
            self.console.event(f"refused backend {peer}, another one is connected")
            return

        self.console.event(f"backend connected {peer}")
        self.backend = writer
        try:
            async for line in reader:
                self.console.command(line.decode().strip())
                self._send(await self._answer(line))
        except ConnectionError:
            pass
        finally:
            self.backend = None
            await stop(self._scanner)
            await stop(self._streamer)
            writer.close()
            self.console.event(f"backend disconnected {peer}")

    async def _scan(self) -> None:
        def on_advertisement(device: BLEDevice, advertisement: AdvertisementData) -> None:
            if ONEPEN_SERVICE in (uuid.lower() for uuid in advertisement.service_uuids):
                self._send(
                    {
                        "type": "advertisement",
                        "time": now(),
                        "address": device.address,
                        "name": advertisement.local_name or device.name,
                        "rssi": advertisement.rssi,
                    }
                )

        self.console.event("scanning for pens...")
        try:
            async with BleakScanner(on_advertisement):
                await asyncio.Event().wait()
        except Exception as error:  # noqa: BLE001
            # such as with bluetooth off. the backend can ask again
            self._error(f"scan failed: {error!r}")

    async def _stream_pen(self, address: str) -> None:
        """Keeps connected to the pen at the address, reconnecting whenever it goes, until cancelled."""
        while True:
            self.console.event(f"looking for {address}...")
            try:
                device = await BleakScanner.find_device_by_address(address, timeout=SCAN_TIMEOUT_SECONDS)
                if device is None:
                    self.console.event("no device found")
                    await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                    continue
                disconnected = asyncio.Event()
                async with BleakClient(device, disconnected_callback=lambda _: disconnected.set()) as client:
                    self.pen = client
                    self._send(
                        {
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
                    )
                    await disconnected.wait()
            except Exception as error:  # noqa: BLE001
                # the pen sleeps and advertises again, so every failure is retried
                self.console.event(f"connection failed: {error!r}")
            finally:
                # also when cancelled, when the backend goes or asks for another pen
                self.pen = None
                self.subscribed.clear()

            self._send({"type": "disconnected", "time": now()})
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"interface to listen on (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"tcp port (default {DEFAULT_PORT})")
    parser.add_argument("--verbose", action="store_true", help="print every command, result and message sent")
    args = parser.parse_args()
    await Bridge(Console(args.verbose)).serve(args.host, args.port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
