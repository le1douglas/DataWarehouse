"""The web app: the walk chosen at /, then its page, /walk/<walk>: the pen, the room selector, and the journal
entries of the open room, every spot of every bench of the walk (settings.py).

The walk is chosen before the pen is connected and the csv is read: each walk has its rooms and its own csv,
and moving to another walk loads another page, so the pen is connected again.

The walk page is used only with a pen connected: without one, a dialog that cannot be closed covers it, with
Connect pen, and goes once a pen connects. The page under it stays as it is: what is typed, and the live
values last received, until the pen that connects sends its own.

The walk page draws and asks; the walk (state/walk.py) decides: which room is open, when a
confirm is allowed, and every read and write of the csv. Each card (ui/journal_entry_card.py) is
drawn again after a confirm, a delete, and a move to another room (ui/room_selector.py).

The page knows nothing of the pen's bytes: the pen, a OnePen connected by the browser over Web Bluetooth
(pens/one_pen.py), gives it decoded values through callbacks.
"""

from datetime import datetime
from pathlib import Path

from nicegui import ui

from webapps.pens.one_pen import OnePen
from webapps.settings import CSV_DIR, EXPORT_DIR, OLD_EXPORT_DIR, TIMEZONE, WALKS
from webapps.state.journal_entry_csv import JournalEntryCsv
from webapps.state.room import BenchSpot
from webapps.state.walk import Walk
from webapps.to_old_journal_entries import write_old_journal_entries
from webapps.ui.confirm_dialog import ConfirmDialog
from webapps.ui.connect_dialog import ConnectDialog
from webapps.ui.journal_entry_card import JournalEntryCard, format_bench_spot_label
from webapps.ui.review_grid import ReviewGrid
from webapps.ui.room_panels import RoomPanels
from webapps.ui.room_selector import RoomSelector
from webapps.ui.settings_dialog import SettingsDialog
from webapps.ui.status_bar import StatusBar


@ui.page("/")
def draw_choice_page() -> None:
    """Which walk: a button for each, to its page."""
    with ui.column().classes("w-full items-center"):
        ui.label("Which walk?").classes("text-xl font-bold")
        for name in WALKS:
            ui.button(format_walk_title(name), on_click=lambda name=name: ui.navigate.to(f"/walk/{name}"))


@ui.page("/walk/{name}")
def draw_walk_page(name: str) -> None:
    """The walk of the name, such as morning. Another name goes back to the choice."""
    if name not in WALKS:
        ui.navigate.to("/")
        return
    ui.page_title(format_walk_title(name))
    csv_path = CSV_DIR / f"journal_entries_{name}.csv"

    # the screen's height, so the cards can fill what the status bar leaves. more scrolls in the room panels
    ui.query(".nicegui-content").classes("h-screen")

    # local to the page. one visitor at a time works on the csv
    walk = Walk(WALKS[name], JournalEntryCsv(csv_path))

    async def go_to_room(name: str) -> None:
        """Moves to the room. Asks first when the current entry is typed, as it would be lost: Cancel stays."""
        if walk.has_typed_entry():
            entry = walk.room.current_entry
            label = format_bench_spot_label((entry.bench, entry.spot))
            question = f"Discard what is typed for {label} in room {walk.room.name}?"
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

    async def ask_delete(bench_spot: BenchSpot) -> None:
        label = format_bench_spot_label(bench_spot)
        if await confirm_dialog.ask(f"Delete the readings of {label}?", "Delete", "delete"):
            walk.delete(bench_spot)
            show_room()
            ui.notify(f"{label} deleted", type="info")

    def show_room() -> None:
        """The open room of the walk, which a confirm or skip may have changed: its name and its cards, slid
        in when it is another room."""
        room_selector.set_room(walk.room.name)
        room_panels.show(walk.get_room_index())

    def notify_error(message: str) -> None:
        ui.notify(message, type="negative")

    def draw_cards() -> None:
        """The cards of the open room as the csv last read says, Drip on top, Drain below."""
        # grow: the height the status bar leaves. auto-rows-[1fr]: rows of one height, never under what a card holds
        with ui.grid().classes("w-full grow auto-rows-[1fr] grid-cols-1 sm:grid-cols-2 gap-4"):
            for bench_spot in walk.bench_spots:
                JournalEntryCard(
                    walk.room.get_entry(bench_spot),
                    walk.room.get_state(bench_spot),
                    is_confirm_allowed=walk.is_confirm_allowed,
                    on_confirm=confirm,
                    on_skip=skip,
                    on_delete=lambda bench_spot=bench_spot: ask_delete(bench_spot),
                )

    # the values go to the open room
    pen = OnePen(on_live=walk.receive_live_value, on_error=notify_error)

    ConnectDialog(pen)

    settings_dialog = SettingsDialog(pen, WALKS[name], csv_path, read_csv_text=walk.read_csv_text)

    status_bar = StatusBar()
    with status_bar.left:
        ui.button("Review", icon="table_view", on_click=lambda: ui.navigate.to(f"/walk/{name}/review")).props("flat")
    with status_bar.center:
        room_selector = RoomSelector(walk.rooms, walk.room.name, on_select=go_to_room)
    with status_bar.right:
        ui.button(icon="settings", on_click=settings_dialog.open).props("flat round")

    # one dialog for the page: a delete, and a move to another room that would lose a typed entry
    confirm_dialog = ConfirmDialog()

    room_panels = RoomPanels(draw_cards, walk.get_room_index())


@ui.page("/walk/{name}/review")
def draw_review_page(name: str) -> None:
    """The csv of the walk of the name as a grid, each value edited in place. Back to the walk page, where
    the pen is connected again, and Export, only once the walk is complete. Another name goes back to the
    choice."""
    if name not in WALKS:
        ui.navigate.to("/")
        return
    journal = JournalEntryCsv(CSV_DIR / f"journal_entries_{name}.csv")
    # read once: the grid adds, deletes and moves no row, so the walk stays as complete as it was
    is_complete = Walk(WALKS[name], journal).is_complete()

    async def export() -> None:
        """Copies the csv to EXPORT_DIR, named by today and the walk, as the datastreamer names its csvs. Asks
        first when today's export of the walk is there: Cancel keeps it.

        - temporary: the same csv in the old format too, in OLD_EXPORT_DIR under the same name, where the
          datastreamer's csvs are: asks first when either is there
        - only once both are written, the csv is emptied for the walk's next pass, and the page goes back to the
          choice: the grid's rows are gone
        """
        file_name = f"{datetime.now(TIMEZONE):%y%m%d}-{WALKS[name].export_number}.csv"
        target = EXPORT_DIR / file_name
        old_target = OLD_EXPORT_DIR / file_name
        existing = [str(path) for path in (target, old_target) if path.exists()]
        if existing and not await confirm_dialog.ask(f"Overwrite {', '.join(existing)}?", "Overwrite", "save"):
            return
        try:
            journal.export(target)
            write_old_journal_entries(journal.read_rows(), WALKS[name], old_target)
        # ValueError: a row the old format cannot place, as its room, bench or spot is not of the walk
        except (OSError, ValueError) as error:
            ui.notify(f"Not exported: {error}", type="negative")
            return
        journal.empty()
        ui.notify(f"Exported to {target.name}, walk emptied", type="positive")
        ui.navigate.to("/")

    ui.page_title(f"{format_walk_title(name)}: review")
    # the screen's height, so the grid fills what the bar leaves
    ui.query(".nicegui-content").classes("h-screen")
    status_bar = StatusBar()
    with status_bar.left:
        ui.button("Back", icon="arrow_back", on_click=lambda: ui.navigate.to(f"/walk/{name}")).props("flat")
    with status_bar.center:
        ui.label(f"{format_walk_title(name)}: review").classes("text-xl font-bold")
    with status_bar.right:
        export_button = ui.button("Export", icon="file_download", on_click=export).props("flat")
        export_button.set_enabled(is_complete)
    # one dialog for the page: an export that would overwrite one
    confirm_dialog = ConfirmDialog()
    ReviewGrid(journal).classes("w-full grow")


def format_walk_title(name: str) -> str:
    """The walk as the pages show it: morning becomes Morning walk."""
    return f"{name.capitalize()} walk"


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
