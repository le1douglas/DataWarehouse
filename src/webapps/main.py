"""The web app, its one page: the pen, the room selector, and the four journal entries of the open room.

The page is used only with a pen connected: without one, a dialog that cannot be closed covers it, with
Connect pen, and goes once a pen connects. The page under it stays as it is: what is typed, and the live
values last received, until the pen that connects sends its own.

The page draws and asks; the daily walk (state/daily_walk.py) decides: which room is open, when a
confirm is allowed, and every read and write of the csv. Each card (ui/journal_entry_card.py) is
drawn again after a confirm, a delete, and a move to another room (ui/room_selector.py).

The page knows nothing of the pen's bytes: the pen, a OnePen connected by the browser over Web Bluetooth
(pens/one_pen.py), gives it decoded values through callbacks.
"""

from pathlib import Path

from nicegui import ui

from webapps.pens.one_pen import OnePen
from webapps.settings import CSV_PATH, ROOMS
from webapps.state.daily_walk import DailyWalk
from webapps.state.journal_entry_csv import JournalEntryCsv
from webapps.state.room import SPOTS
from webapps.ui.confirm_dialog import ConfirmDialog
from webapps.ui.connect_dialog import ConnectDialog
from webapps.ui.journal_entry_card import JournalEntryCard, format_spot_label
from webapps.ui.room_selector import RoomSelector
from webapps.ui.settings_dialog import SettingsDialog
from webapps.ui.status_bar import StatusBar


@ui.page("/")
def draw_page() -> None:
    # at least the screen's height, so the cards can fill what the status bar leaves. more scrolls
    ui.query(".nicegui-content").classes("min-h-screen")

    # local to the page. one visitor at a time works on the csv
    walk = DailyWalk(ROOMS, JournalEntryCsv(CSV_PATH))

    async def go_to_room(name: str) -> None:
        """Moves to the room. Asks first when the current entry is typed, as it would be lost: Cancel stays."""
        if walk.has_typed_entry():
            spot = format_spot_label(walk.room.current_entry.spot)
            question = f"Discard what is typed for {spot} in room {walk.room.name}?"
            if not await confirm_dialog.ask(question, "Discard", "delete_sweep"):
                return
        walk.go_to_room(name)
        show_room()

    def confirm() -> None:
        # Confirm and Enter both come here
        # no toast: the card turning green says it
        if walk.is_confirm_allowed():
            walk.confirm(pen.name)
            show_room()

    def skip() -> None:
        # no toast: the card turning grey says it
        walk.skip()
        show_room()

    async def ask_delete(spot: str) -> None:
        label = format_spot_label(spot)
        if await confirm_dialog.ask(f"Delete the readings of {label}?", "Delete", "delete"):
            walk.delete(spot)
            draw_cards.refresh()
            ui.notify(f"{label} deleted", type="info")

    def show_room() -> None:
        """The open room of the walk, which a confirm or skip may have changed: its name and its cards."""
        room_selector.set_room(walk.room.name)
        draw_cards.refresh()

    def notify_error(message: str) -> None:
        ui.notify(message, type="negative")

    @ui.refreshable
    def draw_cards() -> None:
        """The cards as the csv last read says, Drip on top, Drain below."""
        # grow: the height the status bar leaves. auto-rows-[1fr]: rows of one height, never under what a card holds
        with ui.grid().classes("w-full grow auto-rows-[1fr] grid-cols-1 sm:grid-cols-2 gap-4"):
            for spot in SPOTS:
                JournalEntryCard(
                    walk.room.get_entry(spot),
                    walk.room.get_state(spot),
                    is_confirm_allowed=walk.is_confirm_allowed,
                    on_confirm=confirm,
                    on_skip=skip,
                    on_delete=lambda spot=spot: ask_delete(spot),
                )

    # the values go to the open room
    pen = OnePen(on_live=walk.receive_live_value, on_error=notify_error)

    ConnectDialog(pen)

    settings_dialog = SettingsDialog(pen, read_csv_text=walk.read_csv_text)

    status_bar = StatusBar()
    with status_bar.center:
        room_selector = RoomSelector(walk.rooms, walk.room.name, on_select=go_to_room)
    with status_bar.right:
        ui.button(icon="settings", on_click=settings_dialog.open).props("flat round")

    # one dialog for the page: a delete, and a move to another room that would lose a typed entry
    confirm_dialog = ConfirmDialog()

    draw_cards()


# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # - show=False: there is no browser in the container to open
    # - the reload polls src only, not the whole repo (the working directory), so a save comes through at once
    # - *.js too: pens/one_pen.js is read when its module is imported
    ui.run(
        title="Web apps",
        show=False,
        uvicorn_reload_dirs=str(Path(__file__).parents[1]),
        uvicorn_reload_includes="*.py, *.js",
    )
