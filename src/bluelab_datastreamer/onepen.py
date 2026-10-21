"""Back end of the OnePen: what its bytes mean, and the commands it is sent through the bridge (onepen_bridge.py).

Prints nothing and reads no key: what happens goes to the callbacks of PenClient. What the bytes
mean is in edenic_decompiling_result.md, next to this file. Only the standard library.
"""

import asyncio
import json
import time
from collections.abc import Callable
from datetime import datetime
from itertools import count

RECONNECT_DELAY_SECONDS = 2
# how long the bridge may stay unreachable once it was reached. it is started and ended together
# with the readings (OnePen.cmd), so it is gone that long only when the window was closed
BRIDGE_GONE_SECONDS = 30
# a device is a OnePen when its advertisement lists this service, as in the edenic app
SERVICE = "983dd3da-d46f-bc05-0100-00c278b6b50a"


def characteristic(number: int) -> str:
    # the characteristics of the pen service differ only in the two digits before c278b6b50a
    return f"983dd3da-d46f-bc05-0100-{number:02d}c278b6b50a"


CHARACTERISTICS = {characteristic(number): f"{number:02d}" for number in range(1, 7)}
DEVICE_INFO = characteristic(4)
# the readings saved on the pen by a press of its button. a subscribe makes the pen send them and delete
# them, so it is never subscribed: a reading is taken from the live values only, and a press stays on the
# pen, for the official app
SAVED_READINGS = characteristic(5)
LIVE_READINGS = {characteristic(number) for number in (1, 2, 3)}
# byte 0 of a live reading is a tag that says which quantity its first value is
LIVE_TAGS = {ord("P"): "ph", ord("E"): "ec", ord("T"): "temperature"}
# the mantissa of a value the pen has not got, such as ec with the probe dry (f1d806)
NO_READING = -9999

# ec, ph and temperature, None for a value the pen has not got
Reading = tuple[float | None, float | None, float | None]


def name(uuid: str) -> str:
    return CHARACTERISTICS.get(uuid, uuid)


def value(group: bytes) -> float | None:
    # mantissa as int16 little endian, then the exponent as int8: a negative one multiplies
    mantissa = int.from_bytes(group[:2], "little", signed=True)
    if mantissa == NO_READING:
        return None
    exponent = int.from_bytes(group[2:3], "little", signed=True)
    return mantissa / 10**exponent if exponent >= 0 else mantissa * 10**-exponent


def battery(data: bytes) -> int:
    # byte 1 of 04 is the battery in percent
    return data[1]


def now() -> str:
    # the same time format as the bridge's
    return datetime.now().isoformat(timespec="microseconds")


class BridgeGone(Exception):
    """The bridge was reached, then stayed unreachable for BRIDGE_GONE_SECONDS."""


class PenClient:
    """The OnePen behind the bridge: connects to it, subscribes to its live values and decodes them.

    Until a pen is chosen, the bridge scans, and the OnePens it finds are in pens. Once chosen, the
    bridge connects to that one, again on every connection to the bridge. Every change of the live
    values goes to on_live, and everything else that happens to on_status, as a line of text.
    """

    def __init__(
        self,
        host: str,
        port: int,
        on_live: Callable[[], None],
        on_status: Callable[[str], None],
    ) -> None:
        self.host = host
        self.port = port
        self.on_live = on_live
        self.on_status = on_status
        # the address of the pen chosen, None before the choice
        self.address: str | None = None
        # name and signal strength of the pens found while scanning, by address, in the order found
        self.pens: dict[str, tuple[str, int]] = {}
        # the name of the pen connected last, empty before the first
        self.name = ""
        # true while the bridge is connected to the pen
        self.connected = False
        # the connection to the bridge, None while there is none
        self._writer: asyncio.StreamWriter | None = None
        # the latest live values, None for one the pen has not sent or has not got
        self.live: dict[str, float | None] = dict.fromkeys(LIVE_TAGS.values())
        self._ids = count(1)
        # the commands sent and not answered yet, by id, so a failure can be reported with its command
        self._pending: dict[int, tuple[str, str]] = {}

    @property
    def has_live(self) -> bool:
        return any(live_value is not None for live_value in self.live.values())

    def live_reading(self) -> Reading:
        return self.live["ec"], self.live["ph"], self.live["temperature"]

    def choose(self, address: str) -> None:
        """Connects to the pen at the address, now if the bridge is connected, else as soon as it is."""
        self.address = address
        if self._writer is not None:
            self._command(self._writer, "connect", address=address)

    async def run(self) -> None:
        """Keeps connected to the bridge, reconnecting whenever it goes.

        Raises BridgeGone when the bridge stays unreachable for BRIDGE_GONE_SECONDS after it was
        reached. Before it is first reached, it is waited for as long as it takes.
        """
        # when the bridge went, None while it is connected and before it is first reached
        gone_since: float | None = None
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
            except OSError as error:
                if gone_since is not None and time.monotonic() - gone_since > BRIDGE_GONE_SECONDS:
                    raise BridgeGone(f"the bridge has been gone for more than {BRIDGE_GONE_SECONDS} s") from error
                self.on_status(f"bridge not reachable: {error!r}")
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                continue

            gone_since = None
            self.on_status(f"connected to the bridge at {self.host}:{self.port}")
            self._writer = writer
            # the bridge lets the pen go when the backend goes, so it is asked for again
            if self.address is None:
                self._command(writer, "scan")
            else:
                self._command(writer, "connect", address=self.address)
            try:
                async for line in reader:
                    message = json.loads(line)
                    self._on_message(message)
                    if message["type"] == "connected":
                        # subscriptions end with every pen connection, so they are made again on each
                        self._command(writer, "read", uuid=DEVICE_INFO)
                        for uuid in CHARACTERISTICS:
                            if uuid != SAVED_READINGS:
                                self._command(writer, "subscribe", uuid=uuid)
                        await writer.drain()
            except ConnectionError:
                pass
            finally:
                self._writer = None
                writer.close()
                self._pending.clear()

            gone_since = time.monotonic()
            self.connected = False
            self._forget_live()
            self.on_status("bridge disconnected")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    def _command(self, writer: asyncio.StreamWriter, op: str, **fields: str) -> None:
        request_id = next(self._ids)
        # what the command is about, the characteristic or the address, for a failure
        self._pending[request_id] = (op, fields.get("uuid", fields.get("address", "")))
        writer.write((json.dumps({"id": request_id, "op": op, **fields}) + "\n").encode())

    def _forget_live(self) -> None:
        # so nothing shows the values of a pen that is gone
        self.live.update(dict.fromkeys(self.live))

    def _on_notify(self, message: dict) -> None:
        data = bytes.fromhex(message["hex"])
        # the tag, not the characteristic, says which quantity it is
        if message["uuid"] in LIVE_READINGS and data and data[0] in LIVE_TAGS:
            self.live[LIVE_TAGS[data[0]]] = value(data[1:4])
            self.on_live()

    def _on_message(self, message: dict) -> None:
        kind = message["type"]
        if kind == "notify":
            self._on_notify(message)
        elif kind == "advertisement":
            # the name can be missing from an advertisement, then the one seen before is kept
            known_name = self.pens.get(message["address"], ("?", 0))[0]
            self.pens[message["address"]] = (message["name"] or known_name, message["rssi"])
        elif kind == "result":
            op, uuid = self._pending.pop(message["id"], ("command", str(message["id"])))
            if "error" in message:
                self.on_status(f"{op} {name(uuid)} failed: {message['error']}")
            elif op == "read" and uuid == DEVICE_INFO:
                self.on_status(f"battery {battery(bytes.fromhex(message['hex']))}%")
        elif kind == "connected":
            self.name = message["name"]
            self.connected = True
            self.on_status(f"pen {message['name']} {message['address']} connected")
        else:
            if kind == "disconnected":
                self.connected = False
                self._forget_live()
            self.on_status(json.dumps(message))
