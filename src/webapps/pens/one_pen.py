"""The OnePen, connected by the browser over Web Bluetooth (one_pen.js): its events, and what its bytes mean.

The protocol is that of bluelab_datastreamer/onepen.py, which the web app's image does not have, so the few
lines that decode a live value are here too.
"""

from collections.abc import Callable
from pathlib import Path

from nicegui import ui
from nicegui.events import GenericEventArguments

# the browser's side: the chooser, the connection and the notifications
JS = (Path(__file__).parent / "one_pen.js").read_text()
# the characteristics of the live values, 01 to 03 of the pen service
LIVE_CHARACTERISTICS = {f"983dd3da-d46f-bc05-0100-{number:02d}c278b6b50a" for number in (1, 2, 3)}
# byte 0 of a live value is a tag that says which metric it is
LIVE_TAGS = {ord("P"): "ph", ord("E"): "ec", ord("T"): "temperature"}
# the mantissa of a value the pen has not got, such as ec with the probe dry
NO_READING = -9999


class OnePen:
    """The pen the page talks to: the callbacks, then attach.

    Whether it is connected, and its name once it is, are its own: the page reads them, and keeps no
    copy. What happens goes to the callbacks:
    - on_live: a metric (ph, ec, temperature) and its value, None for one the pen has not got
    - on_disconnected: by the button, or the pen gone, such as out of range
    - on_error: a message, such as a pen that could not be connected

    Made inside a page: its script and its events are of that page.
    """

    def __init__(
        self,
        on_live: Callable[[str, float | None], None],
        on_disconnected: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.on_live = on_live
        self.on_disconnected = on_disconnected
        self.on_error = on_error
        self.connected = False
        # the name of the pen connected last, such as ONE-A1F0, empty before the first
        self.name = ""
        ui.add_body_html(f"<script>{JS}</script>")
        ui.on("one_pen_connected", self._handle_connected)
        ui.on("one_pen_disconnected", self._handle_disconnected)
        ui.on("one_pen_error", self._handle_error)
        ui.on("one_pen_notify", self._handle_notify)

    def attach(self, toggle: ui.button) -> None:
        """Makes the button connect the pen, through Chrome's chooser, or disconnect it: in the browser, as
        Chrome opens the chooser only from a click."""
        toggle.on("click", js_handler="() => toggleOnePen()")

    def _handle_connected(self, event: GenericEventArguments) -> None:
        self.name = event.args["name"]
        self.connected = True

    def _handle_disconnected(self) -> None:
        self.connected = False
        self.on_disconnected()

    def _handle_error(self, event: GenericEventArguments) -> None:
        """The browser has let the connection go, quietly: so it is gone here too, with any value sent before
        the failure, such as one of a pen that went while it was being connected."""
        self._handle_disconnected()
        self.on_error(event.args["message"])

    def _handle_notify(self, event: GenericEventArguments) -> None:
        # the tag, not the characteristic, says which metric it is. other characteristics are ignored
        data = bytes.fromhex(event.args["hex"])
        if event.args["uuid"] in LIVE_CHARACTERISTICS and data and data[0] in LIVE_TAGS:
            self.on_live(LIVE_TAGS[data[0]], decode_value(data[1:4]))


def decode_value(group: bytes) -> float | None:
    """A value of three bytes: the mantissa as int16 little endian, then the exponent as int8, which divides,
    or multiplies when negative. None for a value the pen has not got."""
    mantissa = int.from_bytes(group[:2], "little", signed=True)
    if mantissa == NO_READING:
        return None
    exponent = int.from_bytes(group[2:3], "little", signed=True)
    return mantissa / 10**exponent if exponent >= 0 else mantissa * 10**-exponent
