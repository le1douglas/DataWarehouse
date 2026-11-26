"""The settings dialog of the drip and drain page: the pen connected, its Disconnect, settings.py and the csv."""

from collections.abc import Callable

from nicegui import ui

from webapps import settings
from webapps.pens.one_pen import OnePen


class SettingsDialog(ui.dialog):
    """Disconnect and the name of the pen under it, read from the pen itself, then the settings of settings.py,
    and the csv as it is on disk.

    - every field read only: the settings are changed in settings.py, the pen by Disconnect
    - the pen makes Disconnect disconnect it (attach_disconnect), in the browser
    - the csv read with read_csv_text each time it opens: nothing is written while it is open
    - opened by the page, such as from the gear of the status bar. OK, Escape or a click outside closes it
    - closed by Disconnect too: the connect dialog then covers the page, and this one is not left open
      under it for after the next pen connects
    """

    def __init__(self, pen: OnePen, read_csv_text: Callable[[], str]) -> None:
        super().__init__()
        self._read_csv_text = read_csv_text
        with self, ui.card().classes("w-full"):
            ui.label("Settings").classes("text-lg font-bold")
            disconnect = ui.button("Disconnect", icon="bluetooth_disabled", color="grey", on_click=self.close)
            pen.attach_disconnect(disconnect)
            name = ui.input("Pen").props("readonly").classes("w-full")
            name.bind_value_from(pen, "name")
            ui.separator()
            self._show_settings()
            self._csv = ui.textarea("Csv contents").props("readonly outlined autogrow").classes("w-full font-mono")
            with ui.row().classes("w-full justify-end"):
                ui.button("OK", on_click=self.close)

    def open(self) -> None:
        """Opens with the csv read again."""
        self._csv.set_value(self._read_csv_text())
        super().open()

    def _show_settings(self) -> None:
        """The settings of settings.py, as they were read when the app started."""
        ui.textarea("Rooms", value=", ".join(settings.ROOMS)).props("readonly autogrow").classes("w-full")
        ui.input("Bench", value=settings.BENCH).props("readonly").classes("w-full")
        ui.input("Timezone", value=settings.TIMEZONE.key).props("readonly").classes("w-full")
        ui.input("Csv", value=str(settings.CSV_PATH)).props("readonly").classes("w-full")
