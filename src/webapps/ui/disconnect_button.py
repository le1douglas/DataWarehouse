"""The disconnect button of the drip and drain page: named after the pen connected."""

from nicegui import ui

from webapps.pens.one_pen import OnePen


class DisconnectButton(ui.button):
    """Disconnects the pen (attach_disconnect), its text read from the pen itself: it keeps no copy of the name."""

    def __init__(self, pen: OnePen) -> None:
        super().__init__(icon="bluetooth_disabled", color="grey")
        self.bind_text_from(pen, "name", backward=format_disconnect_text)
        pen.attach_disconnect(self)


def format_disconnect_text(name: str) -> str:
    """The text of the button, such as Disconnect from ONE-A1F0."""
    return f"Disconnect from {name or 'pen without a name'}"
