"""What the walk page and its connect dialog read of a pen: a OnePen (one_pen.py) or, for now, a MockPen
(mock_pen.py)."""

from typing import Protocol

from nicegui import ui


class Pen(Protocol):
    """A pen, made inside a page with on_live and on_error: its live values go to on_live, by metric.

    Whether it is connected or connecting, and its name once it is, are its own: the page reads them, and keeps
    no copy.
    - connected: true while a pen is connected
    - connecting: true from the click on Connect until the pen is connected, or given up
    - name: of the pen connected last, such as ONE-A1F0, written with every entry it confirms
    """

    connected: bool
    connecting: bool
    name: str

    def attach_connect(self, button: ui.button) -> None:
        """Makes the button connect the pen."""
        ...

    def attach_disconnect(self, button: ui.button) -> None:
        """Makes the button disconnect the pen."""
        ...
