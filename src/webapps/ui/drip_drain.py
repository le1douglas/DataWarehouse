"""The drip and drain page: the pen, and the four quadrants of a room (state/room.py), taken one after the other.

The page draws the room and passes on what the user does: the room decides which spot is current, and
confirms and deletes. Each quadrant (ui/quadrant.py) is drawn again from the csv after each.

The page knows nothing of the pen's bytes: the pen gives it decoded values through callbacks. For
now the pen is MockPen.
"""

from collections.abc import Callable

from nicegui import ui

from webapps.pens.mock_pen import MockPen
from webapps.state.journal_csv import CSV_PATH, JournalCsv
from webapps.state.room import SPOTS, Room
from webapps.ui.quadrant import Quadrant

PATH = "/drip-drain"


@ui.page(PATH)
def drip_drain() -> None:
    # local to the page. one visitor at a time works on the csv
    room = Room(JournalCsv(CSV_PATH))

    def can_confirm() -> bool:
        return pen.connected and room.ready

    def confirm() -> None:
        # Confirm and Enter both come here
        if can_confirm():
            spot = room.current_spot
            write(lambda: room.confirm(pen.name), f"{spot} confirmed", "positive")

    async def ask_delete(spot: str) -> None:
        delete_question.set_text(f"Delete the readings of {spot}?")
        if await delete_dialog:
            write(lambda: room.delete(spot), f"{spot} deleted", "info")

    def write(change: Callable[[], None], done: str, kind: str) -> None:
        """Changes the csv, then draws the quadrants again from it and says so."""
        try:
            change()
        except PermissionError:
            ui.notify(f"{CSV_PATH.name} is open in another program: close it and try again", type="negative")
            return
        quadrants.refresh()
        csv_box.set_value(CSV_PATH.read_text())
        ui.notify(done, type=kind)

    def on_error(message: str) -> None:
        ui.notify(message, type="negative")

    @ui.refreshable
    def quadrants() -> None:
        """The quadrants as the csv last read says, Drip on top, Drain below."""
        with ui.grid().classes("w-full grid-cols-1 sm:grid-cols-2 gap-4"):
            for spot in SPOTS:
                Quadrant(
                    spot,
                    row=room.row(spot),
                    draft=room.draft_of(spot),
                    can_confirm=can_confirm,
                    on_confirm=confirm,
                    on_delete=lambda spot=spot: ask_delete(spot),
                )

    # the values go to the current spot. a pen that is gone leaves none on the screen
    pen = MockPen(on_live=room.set_live, on_disconnected=room.forget_live, on_error=on_error)

    with ui.row().classes("w-full items-center"):
        connect = ui.button("Connect pen", icon="bluetooth")
        connect.bind_enabled_from(pen, "connected", backward=lambda connected: not connected)
        disconnect = ui.button("Disconnect", icon="bluetooth_disabled", color="grey")
        disconnect.bind_enabled_from(pen, "connected")
        status = ui.label()
        status.bind_text_from(pen, "connected", backward=lambda connected: pen_status(pen.name, connected))
        pen.attach(connect, disconnect)

    # one dialog for every quadrant, its question set to the spot asked about
    # - Enter deletes, as the focus starts on Delete. Escape cancels
    with ui.dialog() as delete_dialog, ui.card():
        delete_question = ui.label()
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=delete_dialog.close).props("flat")
            delete_answer = ui.button("Delete", icon="delete", color="negative")
            delete_answer.on_click(lambda: delete_dialog.submit(True)).props("autofocus")

    quadrants()

    # for debugging: the csv as it is on disk, read straight from the file when the page opens and after each write.
    # the room has made it, if it was missing
    csv_box = ui.textarea(CSV_PATH.name, value=CSV_PATH.read_text())
    csv_box.props("readonly outlined autogrow").classes("w-full font-mono")


def pen_status(name: str, connected: bool) -> str:
    """The status of the pen, next to its buttons."""
    if not connected:
        return "not connected"
    return f"{name or 'pen without a name'} connected"
