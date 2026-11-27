"""The settings dialog of the home page: every setting of settings.py, read only."""

from nicegui import ui

from webapps import settings


class SettingsDialog(ui.dialog):
    """Every setting of settings.py as the app read it when it started: what every walk shares, then each walk.

    - every field read only: the settings are changed in settings.py
    - opened by the page, such as from the gear of the status bar. OK, Escape or a click outside closes it
    """

    def __init__(self) -> None:
        super().__init__()
        with self, ui.card().classes("w-full"):
            ui.label("Settings").classes("text-lg font-bold")
            _show_shared_settings()
            for name, walk_settings in settings.WALKS.items():
                ui.separator()
                _show_walk_settings(name, walk_settings)
            with ui.row().classes("w-full justify-end"):
                ui.button("OK", on_click=self.close)


def _show_shared_settings() -> None:
    """The timezone, the folders of the csvs and of their export, in both formats, and the mock pen."""
    ui.input("Timezone", value=settings.TIMEZONE.key).props("readonly").classes("w-full")
    ui.input("Csv folder", value=str(settings.CSV_DIR)).props("readonly").classes("w-full")
    ui.input("Export folder", value=str(settings.EXPORT_DIR)).props("readonly").classes("w-full")
    # temporary: the same export in the old format, as long as the review writes it
    ui.input("Old export folder", value=str(settings.OLD_EXPORT_DIR)).props("readonly").classes("w-full")
    # temporary: as long as settings.py has it
    ui.input("Mock pen", value=str(settings.MOCK_PEN)).props("readonly").classes("w-full")


def _show_walk_settings(name: str, walk_settings: settings.WalkSettings) -> None:
    """The walk under its name: its rooms, benches and spots, and the name of its export."""
    ui.label(f"{name.capitalize()} walk").classes("font-bold")
    ui.textarea("Rooms", value=", ".join(walk_settings.rooms)).props("readonly autogrow").classes("w-full")
    ui.input("Benches", value=", ".join(walk_settings.benches)).props("readonly").classes("w-full")
    ui.textarea("Spots", value=", ".join(walk_settings.spots)).props("readonly autogrow").classes("w-full")
    ui.input("Export name", value=f"<yyyy-mm-dd>-{name}.csv").props("readonly").classes("w-full")
