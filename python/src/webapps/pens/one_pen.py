"""The OnePen, connected by the browser over Web Bluetooth (one_pen.js): its events, and what its bytes mean.

The few lines that decode a live value: the protocol was first worked out in the datastreamer (bluelab_datastreamer/
onepen.py, deleted 2026-11-27, in git at 842c7a5).
"""

from collections.abc import Callable
from pathlib import Path

from nicegui import ui
from nicegui.events import GenericEventArguments

from webapps.pens.pen import Pen

# the browser's side: the chooser, the connection and the notifications
JS = (Path(__file__).parent / "one_pen.js").read_text()
# the characteristics of the live values, 01 to 03 of the pen service
LIVE_CHARACTERISTICS = {f"983dd3da-d46f-bc05-0100-{number:02d}c278b6b50a" for number in (1, 2, 3)}
# byte 0 of a live value is a tag that says which metric it is
LIVE_TAGS = {ord("P"): "ph", ord("E"): "ec", ord("T"): "temperature"}
# the mantissa of a value the pen has not got, such as ec with the probe dry
NO_READING = -9999


class OnePen(Pen):
    """The pen the page talks to (Pen): the callbacks, then attach_connect and attach_disconnect.

    What happens goes to the callbacks:
    - on_live: a metric (ph, ec, temperature) and its value, None for one the pen has not got
    - on_error: a message, such as a pen that could not be connected

    connected turns false by the button, or with the pen gone, such as out of range.

    Made inside a page: its script and its events are of that page.
    """

    def __init__(
        self,
        on_live: Callable[[str, float | None], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.on_live = on_live
        self.on_error = on_error
        self.connected = False
        # true from the click on Connect until the pen is connected, or the chooser closed without one
        self.connecting = False
        # the name of the pen connected last, such as ONE-A1F0, empty before the first
        self.name = ""
        ui.add_body_html(f"<script>{JS}</script>")
        ui.on("one_pen_connecting", self._handle_connecting)
        ui.on("one_pen_connected", self._handle_connected)
        ui.on("one_pen_disconnected", self._handle_disconnected)
        ui.on("one_pen_error", self._handle_error)
        ui.on("one_pen_notify", self._handle_notify)

    def attach_connect(self, button: ui.button) -> None:
        """Makes the button connect the pen, through Chrome's chooser: in the browser, as Chrome opens the
        chooser only from a click."""
        button.on("click", js_handler="() => connectOnePen()")

    def attach_disconnect(self, button: ui.button) -> None:
        """Makes the button disconnect the pen, in the browser, which holds the connection."""
        button.on("click", js_handler="() => disconnectOnePen()")

    def _handle_connecting(self, event: GenericEventArguments) -> None:
        self.connecting = event.args["connecting"]

    def _handle_connected(self, event: GenericEventArguments) -> None:
        self.name = event.args["name"]
        self.connected = True

    def _handle_disconnected(self) -> None:
        self.connected = False

    def _handle_error(self, event: GenericEventArguments) -> None:
        """The browser has let the connection go, quietly, such as for a pen that went while it was being
        connected: so it is gone here too."""
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
