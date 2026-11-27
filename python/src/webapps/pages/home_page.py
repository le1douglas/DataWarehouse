"""The page at /: which walk, a button for each, to its page (pages/walk_page.py), and the settings."""

from nicegui import ui

from webapps.settings import WALKS
from webapps.ui.settings_dialog import SettingsDialog
from webapps.ui.status_bar import StatusBar


@ui.page("/")
def draw_home_page(exported: str | None = None) -> None:
    """Which walk: a button for each, to its page. The gear of the status bar opens the settings. exported: the
    file a walk's review has just exported, said in a toast."""
    if exported:
        ui.notify(f"File exported: {exported}", type="positive")
    settings_dialog = SettingsDialog()
    status_bar = StatusBar()
    with status_bar.center:
        ui.label("Which walk?").classes("text-xl font-bold")
    with status_bar.right:
        ui.button(icon="settings", on_click=settings_dialog.open).props("flat round")
    with ui.column().classes("w-full items-center"):
        for name in WALKS:
            ui.button(f"{name.capitalize()} walk", on_click=lambda name=name: ui.navigate.to(f"/walk/{name}"))
