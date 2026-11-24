"""The pen selector of the drip and drain page: Connect, Disconnect and the status of the pen."""

from nicegui import ui

from webapps.pens.mock_pen import MockPen


class PenSelector(ui.row):
    """The buttons and the status of the pen, read from the pen itself: it keeps no copy of either.

    The pen makes the buttons connect and disconnect it (attach), as a real pen needs the click itself.
    """

    def __init__(self, pen: MockPen) -> None:
        super().__init__()
        self.classes("w-full items-center")
        with self:
            connect = ui.button("Connect pen", icon="bluetooth")
            connect.bind_enabled_from(pen, "connected", backward=lambda connected: not connected)
            disconnect = ui.button("Disconnect", icon="bluetooth_disabled", color="grey")
            disconnect.bind_enabled_from(pen, "connected")
            status = ui.label()
            status.bind_text_from(pen, "connected", backward=lambda connected: format_pen_status(pen.name, connected))
        pen.attach(connect, disconnect)


def format_pen_status(name: str, connected: bool) -> str:
    """The status of the pen, next to its buttons."""
    if not connected:
        return "not connected"
    return f"{name or 'pen without a name'} connected"
