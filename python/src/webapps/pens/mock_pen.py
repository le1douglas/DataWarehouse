"""Temporary: a pen without a pen, for working on the walk page with no OnePen at hand (Mock pen in the settings
dialog).

What the page reads of a OnePen, and nothing of Bluetooth:
- connected from the start, so the connect dialog stays closed
- Disconnect and Connect only turn connected off and on
- every second while connected, a live value of each metric, random but plausible
"""

import random
from collections.abc import Callable

from nicegui import app, ui

# the key in app.storage.general of whether the walk page uses a mock pen, set in the settings dialog
# - one value for every browser, kept across restarts
STORAGE_KEY = "mock_pen"
# the name confirmed entries are written with, so a mock reading is never taken for a real one
NAME = "MOCK"
# every metric, the range its random values are drawn from, and the digits they keep
LIVE_RANGES = {"ph": (5.5, 6.5, 2), "ec": (1.5, 3.0, 2), "temperature": (18.0, 24.0, 1)}


def is_mock_pen_on() -> bool:
    """Whether the walk page uses a mock pen: false until the settings dialog sets it."""
    return app.storage.general.get(STORAGE_KEY, False)


class MockPen:
    """In place of a OnePen: same attributes, same attach_connect and attach_disconnect. on_error is never called.

    Made inside a page: its timer is of that page.
    """

    def __init__(
        self,
        on_live: Callable[[str, float | None], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.on_live = on_live
        self.on_error = on_error
        self.connected = True
        self.connecting = False
        self.name = NAME
        ui.timer(1.0, self._send_live_values)

    def attach_connect(self, button: ui.button) -> None:
        button.on_click(lambda: setattr(self, "connected", True))

    def attach_disconnect(self, button: ui.button) -> None:
        button.on_click(lambda: setattr(self, "connected", False))

    def _send_live_values(self) -> None:
        if self.connected:
            for metric, (low, high, digits) in LIVE_RANGES.items():
                self.on_live(metric, round(random.uniform(low, high), digits))
