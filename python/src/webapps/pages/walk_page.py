"""The page of a walk, /walk/<walk>: the pen, the room selector, and the journal entries of the open room, every
spot of every bench of the walk (settings.py).

The walk is chosen before the pen is connected and the csv is read: each walk has its rooms and its own csv,
and moving to another walk loads another page, so the pen is connected again.

The walk page is used only with a pen connected: without one, a dialog that cannot be closed covers it, with
Connect pen, and goes once a pen connects. The page under it stays as it is: what is typed, and the live
values last received, until the pen that connects sends its own.

The walk page draws and asks; the walk (state/walk.py) decides: which room is open, which entry is selected,
when a confirm is allowed, and every read and write of the csv. Each card (ui/journal_entry_card.py) is drawn
again after a selection, a confirm, a delete, and a move to another room (ui/room_selector.py).

The page knows nothing of the pen's bytes: the pen, a OnePen connected by the browser over Web Bluetooth
(pens/one_pen.py), gives it decoded values through callbacks.
"""

from nicegui import events, ui

from webapps.pens.mock_pen import MockPen, is_mock_pen_on
from webapps.pens.one_pen import OnePen
from webapps.pens.pen import Pen
from webapps.settings import WALKS, get_work_in_progress_csv_path
from webapps.state.journal_entry import AbsolutePosition
from webapps.state.journal_entry_csv import JournalEntryCsv
from webapps.state.walk import Walk
from webapps.ui.confirm_dialog import ConfirmDialog
from webapps.ui.connect_dialog import ConnectDialog
from webapps.ui.journal_entry_card import JournalEntryCard, format_bench_spot_label
from webapps.ui.room_panels import RoomPanels
from webapps.ui.room_selector import RoomSelector
from webapps.ui.status_bar import StatusBar

# what each key does, by the name the browser gives it, outside the fields and from the card's alike
# - an arrow key: the walk's direction through the cards of the open room
# - page up and down: the step through the rooms, the previous and the next
CARD_KEYS = {"ArrowLeft": "left", "ArrowRight": "right", "ArrowUp": "up", "ArrowDown": "down"}
ROOM_KEYS = {"PageUp": -1, "PageDown": 1}


@ui.page("/walk/{name}")
def draw_walk_page(name: str) -> None:
    """The walk of the name, such as morning. Another name goes back to the home page."""
    if name not in WALKS:
        ui.navigate.to("/")
        return
    ui.page_title(f"{name.capitalize()} walk")

    # the screen's height, so the cards can fill what the status bar leaves. more scrolls in the room panels
    ui.query(".nicegui-content").classes("h-screen")

    # local to the page. one visitor at a time works on the csv
    walk = Walk(WALKS[name], JournalEntryCsv(get_work_in_progress_csv_path(name)))

    def move_room(step: int) -> None:
        """Moves to the room step rooms away: what is typed in every card is kept, so nothing to ask."""
        # drawn again only when the room changed
        if walk.move_room(step):
            show_room()

    def select(position: AbsolutePosition) -> None:
        walk.select(position)
        show_room()

    def move(direction: str) -> None:
        # drawn again only when the selection moved
        if walk.move(direction):
            show_room()

    def press(key: str) -> None:
        """A key of CARD_KEYS or ROOM_KEYS, by the name the browser gives it. Any other: nothing."""
        if key in CARD_KEYS:
            move(CARD_KEYS[key])
        elif key in ROOM_KEYS:
            move_room(ROOM_KEYS[key])

    def press_by_key(event: events.KeyEventArguments) -> None:
        if event.action.keydown:
            press(event.key.name)

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

    async def ask_delete(position: AbsolutePosition) -> None:
        label = format_bench_spot_label(position)
        if await confirm_dialog.ask(f"Delete the readings of {label}?", "Delete", "delete"):
            walk.delete(position)
            show_room()
            ui.notify(f"{label} deleted", type="info")

    def show_room() -> None:
        """The open room of the walk, which a confirm or skip may have changed: its name and its cards, slid
        in when it is another room."""
        room_selector.set_room(walk.open_room)
        room_panels.show(walk.get_room_index())

    def notify_error(message: str) -> None:
        ui.notify(message, type="negative")

    def draw_cards() -> None:
        """The cards of the open room, from the walk's list, Drip on top, Drain below."""
        # grow: the height the status bar leaves. auto-rows-[1fr]: rows of one height, never under what a card holds
        with ui.grid().classes("w-full grow auto-rows-[1fr] grid-cols-1 sm:grid-cols-2 gap-4"):
            for entry in walk.get_entries(walk.open_room):
                position = entry.get_absolute_position()
                card = JournalEntryCard(
                    entry,
                    is_selected=position == walk.selected,
                    is_confirm_allowed=walk.is_confirm_allowed,
                    on_select=lambda position=position: select(position),
                    on_confirm=confirm,
                    on_skip=skip,
                    on_delete=lambda position=position: ask_delete(position),
                    on_key=press,
                )
                # selected by a key, a confirm or a delete, it may be out of view, such as on the mother walk
                if position == walk.selected:
                    card.scroll_into_view()

    # the values go to the selected entry
    # temporary: the mock pen, when the settings dialog asks for it. read as the page opens
    pen: Pen = (MockPen if is_mock_pen_on() else OnePen)(on_live=walk.receive_live_value, on_error=notify_error)

    ConnectDialog(pen)

    status_bar = StatusBar()
    with status_bar.left:
        ui.button("Back", icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props("flat")
    with status_bar.center:
        room_selector = RoomSelector(walk.open_room, has_room=walk.has_room, on_move=move_room)
    with status_bar.right:
        ui.button("Review", icon="table_view", on_click=lambda: ui.navigate.to(f"/walk/{name}/review")).props("flat")

    # one dialog for the page: a delete
    confirm_dialog = ConfirmDialog()

    # the keys outside the fields. in the fields the card passes them on (JournalEntryCard)
    ui.keyboard(on_key=press_by_key)

    room_panels = RoomPanels(draw_cards, walk.get_room_index())
