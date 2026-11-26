"""The web app, its one page: the pen, the room selector, and the four journal entries of the open room.

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
from webapps.ui.journal_entry_card import JournalEntryCard, format_spot_label
from webapps.ui.pen_selector import PenSelector
from webapps.ui.room_selector import RoomSelector


@ui.page("/")
def draw_page() -> None:
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
        room_selector.set_room(name)
        draw_cards.refresh()

    def is_confirm_allowed() -> bool:
        return walk.is_confirm_allowed(pen.connected)

    def confirm() -> None:
        # Confirm and Enter both come here
        # no toast: the card turning green says it
        if is_confirm_allowed():
            walk.confirm(pen.name)
            redraw()

    def skip() -> None:
        # no toast: the card turning grey says it
        walk.skip()
        redraw()

    async def ask_delete(spot: str) -> None:
        label = format_spot_label(spot)
        if await confirm_dialog.ask(f"Delete the readings of {label}?", "Delete", "delete"):
            walk.delete(spot)
            redraw()
            ui.notify(f"{label} deleted", type="info")

    def redraw() -> None:
        """After a change of the csv: draws the cards and the csv box again from it."""
        draw_cards.refresh()
        csv_box.set_value(walk.read_csv_text())

    def notify_error(message: str) -> None:
        ui.notify(message, type="negative")

    @ui.refreshable
    def draw_cards() -> None:
        """The cards as the csv last read says, Drip on top, Drain below."""
        with ui.grid().classes("w-full grid-cols-1 sm:grid-cols-2 gap-4"):
            for spot in SPOTS:
                JournalEntryCard(
                    walk.room.get_entry(spot),
                    walk.room.get_state(spot),
                    is_confirm_allowed=is_confirm_allowed,
                    on_confirm=confirm,
                    on_skip=skip,
                    on_delete=lambda spot=spot: ask_delete(spot),
                )

    # the values go to the open room. a pen that is gone leaves none on the screen
    pen = OnePen(on_live=walk.receive_live_value, on_disconnected=walk.clear_live_values, on_error=notify_error)

    PenSelector(pen)

    room_selector = RoomSelector(walk.rooms, walk.room.name, on_select=go_to_room)

    # one dialog for the page: a delete, and a move to another room that would lose a typed entry
    confirm_dialog = ConfirmDialog()

    draw_cards()

    # for debugging: the csv as it is on disk, read when the page opens and after each write
    csv_box = ui.textarea(walk.get_csv_name(), value=walk.read_csv_text())
    csv_box.props("readonly outlined autogrow").classes("w-full font-mono")


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
