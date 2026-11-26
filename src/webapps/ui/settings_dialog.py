"""The settings dialog of the drip and drain page: the pen connected, its Disconnect, settings.py and the csv."""

from collections.abc import Callable
from pathlib import Path

from nicegui import ui

from webapps import settings
from webapps.pens.one_pen import OnePen


class SettingsDialog(ui.dialog):
    """Disconnect and the name of the pen under it, read from the pen itself, then the settings: the rooms and
    the benches, the spots and the csv of the walk, the timezone, and where the review exports the csv, in both
    formats. Last the csv as it is on disk.

    - every field read only: the settings are changed in settings.py, the pen by Disconnect
    - the pen makes Disconnect disconnect it (attach_disconnect), in the browser
    - the csv read with read_csv_text each time it opens: nothing is written while it is open
    - opened by the page, such as from the gear of the status bar. OK, Escape or a click outside closes it
    - closed by Disconnect too: the connect dialog then covers the page, and this one is not left open
      under it for after the next pen connects
    """

    def __init__(
        self, pen: OnePen, walk_settings: settings.WalkSettings, csv_path: Path, read_csv_text: Callable[[], str]
    ) -> None:
        super().__init__()
        self._read_csv_text = read_csv_text
        with self, ui.card().classes("w-full"):
            ui.label("Settings").classes("text-lg font-bold")
            disconnect = ui.button("Disconnect", icon="bluetooth_disabled", color="grey", on_click=self.close)
            pen.attach_disconnect(disconnect)
            name = ui.input("Pen").props("readonly").classes("w-full")
            name.bind_value_from(pen, "name")
            ui.separator()
            self._show_settings(walk_settings, csv_path)
            self._csv = ui.textarea("Csv contents").props("readonly outlined autogrow").classes("w-full font-mono")
            with ui.row().classes("w-full justify-end"):
                ui.button("OK", on_click=self.close)

    def open(self) -> None:
        """Opens with the csv read again."""
        self._csv.set_value(self._read_csv_text())
        super().open()

    def _show_settings(self, walk_settings: settings.WalkSettings, csv_path: Path) -> None:
        """The settings of the walk and the timezone, as settings.py had them when the app started, the csv, and
        the folders and name of its export, in both formats."""
        ui.textarea("Rooms", value=", ".join(walk_settings.rooms)).props("readonly autogrow").classes("w-full")
        ui.input("Benches", value=", ".join(walk_settings.benches)).props("readonly").classes("w-full")
        ui.textarea("Spots", value=", ".join(walk_settings.spots)).props("readonly autogrow").classes("w-full")
        ui.input("Timezone", value=settings.TIMEZONE.key).props("readonly").classes("w-full")
        ui.input("Csv", value=str(csv_path)).props("readonly").classes("w-full")
        ui.input("Export folder", value=str(settings.EXPORT_DIR)).props("readonly").classes("w-full")
        # temporary: the same export in the old format, as long as the review writes it
        ui.input("Old export folder", value=str(settings.OLD_EXPORT_DIR)).props("readonly").classes("w-full")
        export_name = f"<yymmdd>-{walk_settings.export_number}.csv"
        ui.input("Export name", value=export_name).props("readonly").classes("w-full")
