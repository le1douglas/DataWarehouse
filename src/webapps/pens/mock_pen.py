"""A OnePen that is not there: values of a drip or drain line every second, for working without a pen."""

import random
from collections.abc import Callable

from nicegui import ui

NAME = "MOCK-PEN"
INTERVAL_SECONDS = 1.0
# per quantity: where it starts, how far it may move in a step, and the range it stays in
# - about what a drip or drain line reads
WALKS = {
    "ph": (5.8, 0.03, 5.0, 7.0),
    "ec": (2.3, 0.05, 0.5, 4.0),
    "temperature": (21.0, 0.1, 15.0, 28.0),
}
# the share of the way back to the start a value moves in a step, so it wanders around it, not off to the range's end
PULL = 0.05


class MockPen:
    """The pen the page talks to: the callbacks, then attach.

    Whether it is connected, and its name once it is, are its own: the page reads them, and keeps no
    copy. What happens goes to the callbacks:
    - on_live: a quantity (ph, ec, temperature) and its value, None for one the pen has not got
    - on_disconnected
    - on_error: a message

    Every value moves a little each step, a random walk around its start within its range, so the
    screen looks like a pen in the water. Made inside a page, as its timer is of that page.
    """

    def __init__(
        self,
        on_live: Callable[[str, float | None], None],
        on_disconnected: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.on_live = on_live
        self.on_disconnected = on_disconnected
        # on_error is never called: a pen that is not there cannot fail
        self.connected = False
        # the name of the pen connected last, empty before the first
        self.name = ""
        self.values = {quantity: start for quantity, (start, _, _, _) in WALKS.items()}
        self._timer = ui.timer(INTERVAL_SECONDS, self._step, active=False)

    def attach(self, connect: ui.button, disconnect: ui.button) -> None:
        """Makes the buttons connect and disconnect the pen."""
        connect.on_click(self.connect)
        disconnect.on_click(self.disconnect)

    def connect(self) -> None:
        self.name = NAME
        self.connected = True
        self._timer.activate()

    def disconnect(self) -> None:
        self._timer.deactivate()
        self.connected = False
        self.on_disconnected()

    def _step(self) -> None:
        for quantity, (start, step, low, high) in WALKS.items():
            value = self.values[quantity]
            moved = value + random.uniform(-step, step) + PULL * (start - value)
            self.values[quantity] = min(high, max(low, moved))
            # two decimals, as the pen sends them
            self.on_live(quantity, round(self.values[quantity], 2))
