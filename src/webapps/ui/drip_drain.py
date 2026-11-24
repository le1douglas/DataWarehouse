"""The drip and drain page: the pen, and the four quadrants of a room, taken one after the other.

Each quadrant (ui/quadrant.py) shows its quadrant state (state/quadrant_state.py). The spots are taken in
the order of SPOTS: the current one, being taken, is the first without a row in the csv. Only it has the
live values, fields to type in and a Confirm that works, and the focus is in its ml, so Enter confirms.
Deleting a row makes its spot one without a row again, so it is taken again before going on.

The csv (state/journal_csv.py) is the only record of what is confirmed, and so of which spot is current:
confirm appends a row, delete removes it, and the quadrants are drawn from it again after each, and when
the page opens.

The page knows nothing of the pen's bytes: the pen gives it decoded values through callbacks. For
now the pen is MockPen.
"""

from nicegui import ui

from webapps.pens.mock_pen import MockPen
from webapps.state.journal_csv import CSV_PATH, JournalCsv
from webapps.state.quadrant_state import QuadrantState
from webapps.ui.quadrant import Quadrant

PATH = "/drip-drain"
# the spots of a room in the order they are taken, as LINE_NAMES in bluelab_datastreamer/drip_drain.py
SPOTS = ("Drip Left", "Drip Right", "Drain Left", "Drain Right")


@ui.page(PATH)
def drip_drain() -> None:
    # local to the page. one visitor at a time works on the csv
    connection = {"connected": False, "device": "", "status": "not connected"}
    states = {spot: QuadrantState(spot) for spot in SPOTS}
    quadrants: dict[str, Quadrant] = {}
    journal = JournalCsv(CSV_PATH)
    # what the text box shows
    csv_view = {"text": ""}

    def current() -> str | None:
        """The spot being taken: the first without a row in the csv. None when every spot has one."""
        return next((spot for spot in SPOTS if not states[spot].confirmed), None)

    def sync() -> None:
        """Draws the quadrant states and the text box from the csv again."""
        rows = journal.rows()
        for state in states.values():
            state.load(rows.get(state.csv_spot))
        csv_view["text"] = journal.text()
        refresh()

    def refresh() -> None:
        spot = current()
        for other, quadrant in quadrants.items():
            # a spot no longer current, after a delete before it, keeps no live values of the pen
            if other != spot:
                states[other].forget_live()
            quadrant.set_current(other == spot, connection["connected"])

    def focus_current() -> None:
        if (spot := current()) is not None:
            quadrants[spot].focus_ml()

    def confirm(spot: str) -> None:
        # only the current spot, ready and with the pen connected
        if not quadrants[spot].can_confirm:
            return
        try:
            journal.append(states[spot].to_row(connection["device"]))
        except PermissionError:
            ui.notify(f"{CSV_PATH.name} is open in another program: close it and confirm again", type="negative")
            return
        sync()
        focus_current()
        ui.notify(f"{spot} confirmed", type="positive")

    async def ask_delete(spot: str) -> None:
        delete_question.set_text(f"Delete the readings of {spot}?")
        if not await delete_dialog:
            return
        try:
            journal.delete(states[spot].csv_spot)
        except PermissionError:
            ui.notify(f"{CSV_PATH.name} is open in another program: close it and delete again", type="negative")
            return
        sync()
        focus_current()
        ui.notify(f"{spot} deleted", type="info")

    def on_live(quantity: str, value: float | None) -> None:
        if (spot := current()) is not None:
            states[spot].set_live(quantity, value)

    def on_connected(name: str) -> None:
        connection.update(connected=True, device=name, status=f"{name or 'pen without a name'} connected")
        refresh()

    def on_disconnected() -> None:
        connection.update(connected=False, status="not connected")
        # so the current quadrant keeps no values of a pen that is gone
        if (spot := current()) is not None:
            states[spot].forget_live()
        refresh()

    def on_error(message: str) -> None:
        ui.notify(message, type="negative")

    with ui.row().classes("w-full items-center"):
        connect = ui.button("Connect pen", icon="bluetooth")
        connect.bind_enabled_from(connection, "connected", backward=lambda connected: not connected)
        disconnect = ui.button("Disconnect", icon="bluetooth_disabled", color="grey")
        disconnect.bind_enabled_from(connection, "connected")
        ui.label().bind_text_from(connection, "status")
        pen = MockPen(on_live=on_live, on_connected=on_connected, on_disconnected=on_disconnected, on_error=on_error)
        pen.attach(connect, disconnect)

    # one dialog for every quadrant, its question set to the spot asked about
    # - Enter deletes, as the focus starts on Delete. Escape cancels
    with ui.dialog() as delete_dialog, ui.card():
        delete_question = ui.label()
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=delete_dialog.close).props("flat")
            delete_answer = ui.button("Delete", icon="delete", color="negative")
            delete_answer.on_click(lambda: delete_dialog.submit(True)).props("autofocus")

    # the quadrants in the order they are taken: Drip on top, Drain below
    with ui.grid().classes("w-full grid-cols-1 sm:grid-cols-2 gap-4"):
        for spot, state in states.items():
            quadrants[spot] = Quadrant(
                state,
                on_confirm=lambda spot=spot: confirm(spot),
                on_delete=lambda spot=spot: ask_delete(spot),
            )

    # the csv as it is on disk, read only
    csv_box = ui.textarea(CSV_PATH.name).props("readonly outlined autogrow").classes("w-full font-mono")
    csv_box.bind_value_from(csv_view, "text")

    sync()
    # the focus in the current ml once the browser is connected, which it is not while the page is built
    ui.context.client.on_connect(focus_current)
