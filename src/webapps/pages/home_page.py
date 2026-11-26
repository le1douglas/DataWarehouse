"""The page at /: which walk, a button for each, to its page (pages/walk_page.py)."""

from nicegui import ui

from webapps.settings import WALKS


@ui.page("/")
def draw_home_page() -> None:
    """Which walk: a button for each, to its page."""
    with ui.column().classes("w-full items-center"):
        ui.label("Which walk?").classes("text-xl font-bold")
        for name in WALKS:
            ui.button(f"{name.capitalize()} walk", on_click=lambda name=name: ui.navigate.to(f"/walk/{name}"))
