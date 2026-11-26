"""One journal entry of the drip and drain page as a card: what it shows, nothing of what it needs."""

from collections.abc import Callable
from typing import Any

from nicegui import ui

from webapps.state.journal_entry import ML_DIGITS, NOT_RECEIVED, JournalEntry
from webapps.state.journal_entry_csv import NOT_AVAILABLE, format_live_value
from webapps.state.journal_entry_state import JournalEntryState

# the live values shown, by the name the pen gives them
LABELS = {"ph": "pH", "ec": "EC", "temperature": "Temp"}
# the look of the card by its state, none while pending
LOOKS = {JournalEntryState.CURRENT: "ring-4 ring-blue-500", JournalEntryState.CONFIRMED: "bg-green-1"}
# the live values of an entry without a reading, greyed out: they are written n.a
GREYED_OUT = "opacity-30"


class JournalEntryCard(ui.card):
    """A journal entry as a card, drawn again by the page whenever the csv changes.

    Every card has the same parts in the same place: the live values, the ml, the remarks and the
    buttons. Only what is in them differs, by the state of the entry:
    - confirmed: its row as the csv has it, read only, and Delete (on_delete). a skipped one greyed out
    - current: bound to the entry, so the live values and the typing show by themselves. Confirm, or
      Enter in a field (on_confirm), enabled while is_confirm_allowed says so, and Skip (on_skip)
    - pending: empty, disabled
    """

    def __init__(
        self,
        entry: JournalEntry,
        state: JournalEntryState,
        is_confirm_allowed: Callable[[], bool],
        on_confirm: Callable[[], Any],
        on_skip: Callable[[], Any],
        on_delete: Callable[[], Any],
    ) -> None:
        super().__init__()
        self._is_confirm_allowed = is_confirm_allowed
        self.classes(f"w-full {LOOKS.get(state, '')}")
        # each step places its elements in the card, so all of them inside it
        with self:
            self._draw_parts(entry)
            # the buttons last, drawn by each, so they are in the same place on every card
            if state == JournalEntryState.CONFIRMED:
                self._show_confirmed(entry, on_delete)
            elif state == JournalEntryState.CURRENT:
                self._bind_current(entry, on_confirm, on_skip)
            else:
                self._disable_pending()

    @property
    def is_confirm_allowed(self) -> bool:
        return self._is_confirm_allowed()

    def _draw_parts(self, entry: JournalEntry) -> None:
        """The parts every card has, empty: its room and spot, the live values, the ml, the remarks."""
        ui.label(_format_card_title(entry)).classes("text-lg font-bold")
        # side by side: the labels in a row, the values in a row under them
        self._live_grid = ui.grid(columns=len(LABELS)).classes("w-full text-center gap-y-0")
        with self._live_grid:
            for label in LABELS.values():
                ui.label(label).classes("text-grey-7")
            self._values = {metric: ui.label("–").classes("font-mono text-lg") for metric in LABELS}
        # text with a mask of digits, not ui.number: a number field takes e, + and -, and reads 4e2 as 400
        # - inputmode: the number pad on a phone
        self._ml = ui.input("ml").classes("w-full").props(f'mask="{"#" * ML_DIGITS}" inputmode=numeric')
        self._remarks = ui.input("remarks (optional)").classes("w-full")
        self._fields = (self._ml, self._remarks)

    def _show_confirmed(self, entry: JournalEntry, on_delete: Callable[[], Any]) -> None:
        """Its row as the csv has it, read only, and Delete."""
        for metric, value in self._values.items():
            value.set_text(format_live_value(metric, getattr(entry, metric)))
        self._ml.value = NOT_AVAILABLE if entry.ml is None else str(entry.ml)
        self._remarks.value = entry.remarks
        # read only, not disabled: shown as clearly as when it was typed
        for field in self._fields:
            field.props("readonly")
        self._show_reading(entry.has_reading())
        ui.button("Delete", icon="delete", color="negative", on_click=on_delete).classes("w-full")

    def _bind_current(self, entry: JournalEntry, on_confirm: Callable[[], Any], on_skip: Callable[[], Any]) -> None:
        """Bound to the entry, so the live values and the typing show by themselves, Confirm and Skip."""
        for metric, value in self._values.items():
            value.bind_text_from(entry, metric, backward=lambda v, q=metric: _format_shown_value(q, v))
        # autofocus: the focus in it whenever the card is drawn, so the ml is typed straight away
        self._ml.props("autofocus")
        self._ml.bind_value(entry, "ml", forward=lambda text: int(text) if text else None, backward=_format_ml)
        self._remarks.bind_value(entry, "remarks")
        for field in self._fields:
            field.on("keydown.enter", on_confirm)
        confirm, skip = self._draw_confirm_and_skip()
        confirm.on_click(on_confirm)
        confirm.bind_enabled_from(self, "is_confirm_allowed")
        skip.on_click(on_skip)

    def _disable_pending(self) -> None:
        """Empty and disabled, Confirm and Skip too."""
        for field in self._fields:
            field.disable()
        for button in self._draw_confirm_and_skip():
            button.disable()

    def _draw_confirm_and_skip(self) -> tuple[ui.button, ui.button]:
        """Confirm, wide, and Skip next to it: no reading for the spot, its remarks kept."""
        with ui.row().classes("w-full no-wrap"):
            confirm = ui.button("Confirm", icon="check").classes("grow")
            skip = ui.button("Skip", icon="skip_next", color="grey").props("outline")
        return confirm, skip

    def _show_reading(self, has_reading: bool) -> None:
        """An entry without a reading: its live values greyed out and its ml disabled."""
        if not has_reading:
            self._live_grid.classes(GREYED_OUT)
        self._ml.set_enabled(has_reading)


def _format_card_title(entry: JournalEntry) -> str:
    """The room and the spot of the card: [1.30] Drip Left."""
    return f"[{entry.room}] {format_spot_label(entry.spot)}"


def format_spot_label(spot: str) -> str:
    """The spot as the page shows it: drip_left becomes Drip Left."""
    return spot.replace("_", " ").title()


def _format_ml(ml: int | None) -> str:
    """The ml as the field shows it, empty for none."""
    return "" if ml is None else str(ml)


def _format_shown_value(metric: str, value: float | str | None) -> str:
    """A live value as the card shows it: – until it is received, then as the csv writes it."""
    if value == NOT_RECEIVED:
        return "–"
    return format_live_value(metric, value)
