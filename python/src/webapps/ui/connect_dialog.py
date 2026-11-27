"""The connect dialog of the drip and drain page: over the page whenever no pen is connected."""

from nicegui import ui

from webapps.pens.one_pen import OnePen


class ConnectDialog(ui.dialog):
    """Connect pen, open while the pen is not connected, read from the pen itself: it keeps no copy.

    - persistent: Escape and a click outside do not close it, only a pen that connects
    - Connect pen, or a spinner while the pen is connecting: from the click, with Chrome's chooser open
    - the pen makes the button connect it (attach_connect), as Chrome opens its chooser only from a click
    """

    def __init__(self, pen: OnePen) -> None:
        super().__init__()
        self.props("persistent")
        self.bind_value_from(pen, "connected", backward=lambda connected: not connected)
        with self, ui.card().classes("items-center"):
            ui.label("OnePen is disconnected").classes("text-lg font-bold")
            connect = ui.button("Connect pen", icon="bluetooth")
            connect.bind_visibility_from(pen, "connecting", backward=lambda connecting: not connecting)
            with ui.row().classes("items-center") as connecting:
                ui.spinner()
                ui.label("Connecting...")
            connecting.bind_visibility_from(pen, "connecting")
        pen.attach_connect(connect)
