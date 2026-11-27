"""The pen dialog of the walk page: the pen connected and its Disconnect."""

from nicegui import ui

from webapps.pens.one_pen import OnePen


class PenDialog(ui.dialog):
    """The name of the pen, read from the pen itself, and Disconnect.

    - the pen makes Disconnect disconnect it (attach_disconnect), in the browser
    - opened by the page, such as from the bluetooth icon of the status bar. OK, Escape or a click outside closes it
    - closed by Disconnect too: the connect dialog then covers the page, and this one is not left open
      under it for after the next pen connects
    """

    def __init__(self, pen: OnePen) -> None:
        super().__init__()
        with self, ui.card().classes("w-full"):
            ui.label("Pen").classes("text-lg font-bold")
            name = ui.input("Name").props("readonly").classes("w-full")
            name.bind_value_from(pen, "name")
            disconnect = ui.button("Disconnect", icon="bluetooth_disabled", color="grey", on_click=self.close)
            pen.attach_disconnect(disconnect)
            with ui.row().classes("w-full justify-end"):
                ui.button("OK", on_click=self.close)
