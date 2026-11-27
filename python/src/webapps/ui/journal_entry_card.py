"""One journal entry of the drip and drain page as a card: what it shows, nothing of what it needs."""

from collections.abc import Callable
from typing import Any

from nicegui import ui

from webapps.state.journal_entry import ML_DIGITS, NOT_RECEIVED, AbsolutePosition, JournalEntry
from webapps.state.journal_entry_csv import NOT_AVAILABLE, format_live_value

# the live values shown, by the name the pen gives them
LABELS = {"ph": "pH", "ec": "EC", "temperature": "Temp"}
# the look of the card by its status
CONFIRMED_LOOK = "bg-green-1"
SELECTED_LOOK = "ring-4 ring-blue-500"
# the live values of the selected entry, as the pen streams them. a confirmed one's are solid
STREAMING_LOOK = "animate-pulse"
# its pace, half of Tailwind's 2s. inline: it always wins over the class's own
STREAMING_PACE = "animation-duration: 1s"
# a tap anywhere on it selects it
UNCONFIRMED_LOOK = "cursor-pointer"
# the live values of an entry without a reading, greyed out: they are written n.a
GREYED_OUT = "opacity-30"
# the arrow keys the ml passes on, by their Vue key modifier: the name the browser gives them
ARROW_KEYS = {"left": "ArrowLeft", "right": "ArrowRight", "up": "ArrowUp", "down": "ArrowDown"}


class JournalEntryCard(ui.card):
    """A journal entry as a card, drawn again by the page whenever the walk's selection or list changes.

    It stores nothing: it shows the entry, and what is typed goes straight into it. Every card has the same parts
    in the same place: the live values, the ml, the remarks and the buttons. Only what is in them differs, by the
    status of the entry, derived and never stored:
    - confirmed (its reading_status not in_progress): read only, and Delete (on_delete). a skipped one greyed out
    - selected: bound to the entry, so the live values and the typing show by themselves, the live values
      blinking. Confirm, or Enter in a field (on_confirm), enabled while is_confirm_allowed says so, and Skip
      (on_skip). an arrow key in the ml moves to another card (on_move, the key's name)
    - unconfirmed: bound to the entry too, no live values: the walk clears them when it is deselected. Confirm and
      Skip disabled. a tap anywhere on it selects it (on_select)
    """

    def __init__(
        self,
        entry: JournalEntry,
        is_selected: bool,
        is_confirm_allowed: Callable[[], bool],
        on_select: Callable[[], Any],
        on_confirm: Callable[[], Any],
        on_skip: Callable[[], Any],
        on_delete: Callable[[], Any],
        on_move: Callable[[str], Any],
    ) -> None:
        super().__init__()
        self._is_confirm_allowed = is_confirm_allowed
        self.classes("w-full")
        # each step places its elements in the card, so all of them inside it
        with self:
            self._draw_parts(entry)
            # the space between grows with the card, so the buttons are at its bottom
            ui.space()
            # the buttons last, drawn by each, so they are in the same place on every card
            if entry.is_confirmed():
                self._show_confirmed(entry, on_delete)
            elif is_selected:
                self._bind_entry(entry)
                self._enable_selected(on_confirm, on_skip, on_move)
            else:
                self._bind_entry(entry)
                self._enable_unconfirmed(on_select)

    @property
    def is_confirm_allowed(self) -> bool:
        return self._is_confirm_allowed()

    def scroll_into_view(self) -> None:
        """Scrolls the panel until the card is in view, when it is not: Quasar's autofocus focuses without a
        scroll."""
        # - JavaScript: no Python API scrolls to an element
        # - setTimeout: Vue draws the card after its update, which may reach the browser after this
        # - scroll-m-2: its ring in view too, not cut at the panel's edge
        self.classes("scroll-m-2")
        ui.run_javascript(
            f"setTimeout(() => getHtmlElement({self.id})?.scrollIntoView({{block: 'nearest', behavior: 'smooth'}}))"
        )

    def _draw_parts(self, entry: JournalEntry) -> None:
        """The parts every card has, empty: its room and spot, the live values, the ml, the remarks."""
        ui.label(_format_card_title(entry)).classes("text-lg font-bold")
        # side by side, the ml first: the labels in a row, the values in a row under them
        self._live_grid = ui.grid(columns=len(LABELS) + 1).classes("w-full text-center gap-y-0 items-center")
        with self._live_grid:
            for label in ("ml", *LABELS.values()):
                ui.label(label).classes("text-grey-7")
            # text with a mask of digits, not ui.number: a number field takes e, + and -, and reads 4e2 as 400
            # - inputmode: the number pad on a phone
            # - input-class: its text as the live values', its underline the only sign it is typed in
            self._ml = ui.input(placeholder="–").props(
                f'mask="{"#" * ML_DIGITS}" inputmode=numeric dense hide-bottom-space '
                'input-class="text-center font-mono text-lg"'
            )
            self._values = {metric: ui.label("–").classes("font-mono text-lg") for metric in LABELS}
        self._remarks = ui.input("remarks (optional)").classes("w-full")
        self._fields = (self._ml, self._remarks)

    def _show_confirmed(self, entry: JournalEntry, on_delete: Callable[[], Any]) -> None:
        """Its values, read only, and Delete."""
        self.classes(CONFIRMED_LOOK)
        for metric, value in self._values.items():
            value.set_text(format_live_value(metric, getattr(entry, metric)))
        self._ml.value = NOT_AVAILABLE if entry.ml is None else str(entry.ml)
        self._remarks.value = entry.remarks
        # read only, not disabled: shown as clearly as when it was typed
        for field in self._fields:
            field.props("readonly")
        self._show_reading(entry.has_reading())
        ui.button("Delete", icon="delete", color="negative", on_click=on_delete).classes("w-full")

    def _bind_entry(self, entry: JournalEntry) -> None:
        """Bound to the unconfirmed entry, so the live values and the typing show by themselves."""
        for metric, value in self._values.items():
            value.bind_text_from(entry, metric, backward=lambda v, q=metric: _format_shown_value(q, v))
        self._ml.bind_value(entry, "ml", forward=lambda text: int(text) if text else None, backward=_format_ml)
        self._remarks.bind_value(entry, "remarks")

    def _enable_selected(
        self, on_confirm: Callable[[], Any], on_skip: Callable[[], Any], on_move: Callable[[str], Any]
    ) -> None:
        """Confirm, or Enter in a field, and Skip. An arrow key in the ml moves to another card."""
        self.classes(SELECTED_LOOK)
        for value in self._values.values():
            value.classes(STREAMING_LOOK).style(STREAMING_PACE)
        # autofocus: the focus in it whenever the card is drawn, so the ml is typed straight away
        self._ml.props("autofocus")
        for field in self._fields:
            field.on("keydown.enter", on_confirm)
        # - the ml only: a few digits, its cursor hardly needed
        # - in the remarks the arrow keys stay with the text
        for modifier, key in ARROW_KEYS.items():
            self._ml.on(f"keydown.{modifier}", lambda key=key: on_move(key))
        confirm, skip = self._draw_confirm_and_skip()
        confirm.on_click(on_confirm)
        confirm.bind_enabled_from(self, "is_confirm_allowed")
        skip.on_click(on_skip)

    def _enable_unconfirmed(self, on_select: Callable[[], Any]) -> None:
        """A tap anywhere on it selects it, in a field too. Confirm and Skip disabled: only the selected entry is
        confirmed."""
        self.classes(UNCONFIRMED_LOOK)
        self.on("click", on_select)
        for button in self._draw_confirm_and_skip():
            button.disable()

    def _draw_confirm_and_skip(self) -> tuple[ui.button, ui.button]:
        """Skip and Confirm side by side, Confirm on the right. Skip: no reading for the spot, its remarks kept."""
        # - no-wrap and flex-1: side by side and the same width on any screen
        with ui.row().classes("w-full no-wrap"):
            skip = ui.button("Skip", icon="skip_next", color="grey").props("outline").classes("flex-1")
            confirm = ui.button("Confirm", icon="check").classes("flex-1")
        return confirm, skip

    def _show_reading(self, has_reading: bool) -> None:
        """An entry without a reading: its live values greyed out and its ml disabled."""
        if not has_reading:
            self._live_grid.classes(GREYED_OUT)
        self._ml.set_enabled(has_reading)


def format_bench_spot_label(position: AbsolutePosition) -> str:
    """The bench and spot of the absolute position as the page names them in a question: T4 Drip Left."""
    _, bench, spot = position
    return f"{_format_bench_label(bench)} {_format_spot_label(spot)}"


def _format_card_title(entry: JournalEntry) -> str:
    """The room, the bench and the spot of the card: [1.30, T4] Drip Left."""
    return f"[{entry.room}, {_format_bench_label(entry.bench)}] {_format_spot_label(entry.spot)}"


def _format_bench_label(bench: str) -> str:
    """The bench as the page shows it: 4 becomes T4."""
    return f"T{bench}"


def _format_spot_label(spot: str) -> str:
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
