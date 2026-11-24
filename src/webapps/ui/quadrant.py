"""One quadrant of the drip and drain page: the state of a spot as a card."""

from collections.abc import Callable
from typing import Any

from nicegui import ui

from webapps.state.quadrant_state import DECIMALS, ML_DIGITS, NOT_RECEIVED, QuadrantState

# the live values shown, by the name the pen gives them, with their decimals as in the csv (DECIMALS)
LABELS = {"ph": "pH", "ec": "EC", "temperature": "Temp"}
# the look of the card
# - CARD always, CURRENT while it is the one being taken, CONFIRMED once it has its row
CARD = "w-full"
CURRENT = "ring-4 ring-blue-500"
CONFIRMED = "bg-green-1"


class Quadrant(ui.card):
    """Shows a quadrant state and takes its buttons: changes nothing in it itself.

    Every value is bound to the quadrant state, so a change to it shows by itself. The page says whether
    it is the current quadrant, the one being taken, and whether the pen is connected (set_current), and
    hears of the buttons through the callbacks:
    - on_confirm: Confirm, or Enter in one of its fields
    - on_delete: Delete, once confirmed
    """

    def __init__(self, state: QuadrantState, on_confirm: Callable[[], Any], on_delete: Callable[[], Any]) -> None:
        super().__init__()
        self.state = state
        self._current = False
        self._connected = False
        self.classes(CARD)
        with self:
            ui.label(state.spot).classes("text-lg font-bold")
            # side by side: the labels in a row, the values in a row under them
            with ui.grid(columns=len(LABELS)).classes("w-full text-center gap-y-0"):
                for label in LABELS.values():
                    ui.label(label).classes("text-grey-7")
                for quantity in LABELS:
                    value = ui.label().classes("font-mono text-lg")
                    value.bind_text_from(state, quantity, backward=lambda v, q=quantity: shown(q, v))
            # text with a mask of digits, not ui.number: a number field takes e, + and -, and reads 4e2 as 400
            # - inputmode: the number pad on a phone
            ml = ui.input("ml").classes("w-full").props(f'mask="{"#" * ML_DIGITS}" inputmode=numeric')
            ml.bind_value(state, "ml", forward=lambda text: int(text) if text else None, backward=ml_text)
            remarks = ui.input("remarks (optional)").classes("w-full").bind_value(state, "remarks")
            self._ml = ml
            # enabled by set_current, not bound: a binding comes up to 0.1 s late, too late for focus_ml after a delete
            self._fields = (ml, remarks)
            for field in self._fields:
                field.on("keydown.enter", on_confirm)
            # confirm until confirmed, then delete
            confirm = ui.button("Confirm", icon="check", on_click=on_confirm).classes("w-full")
            confirm.bind_enabled_from(self, "can_confirm")
            confirm.bind_visibility_from(state, "confirmed", backward=lambda confirmed: not confirmed)
            delete = ui.button("Delete", icon="delete", color="negative", on_click=on_delete)
            delete.classes("w-full").props("outline").bind_visibility_from(state, "confirmed")

    @property
    def can_confirm(self) -> bool:
        return self._connected and self._current and self.state.ready

    def set_current(self, current: bool, connected: bool) -> None:
        """Whether this is the quadrant being taken, and whether the pen is connected. Only the current one
        can be typed in."""
        self._current = current
        self._connected = connected
        looks = [CURRENT if current else "", CONFIRMED if self.state.confirmed else ""]
        # remove and add, not replace, which would remove nicegui-card too, and with it the padding of the card
        self.classes(remove=f"{CURRENT} {CONFIRMED}").classes(" ".join(looks))
        for field in self._fields:
            field.enabled = current

    def focus_ml(self) -> None:
        """Puts the focus in the ml field, to type it straight away. Only the current one: the others are disabled."""
        if self._current:
            self._ml.run_method("focus")


def ml_text(ml: int | None) -> str:
    """The ml as the field shows it, empty for none."""
    return "" if ml is None else str(ml)


def shown(quantity: str, value: float | str | None) -> str:
    """A live value as the card shows it."""
    if value == NOT_RECEIVED:
        return "–"
    # a dry probe has no ec, and its ph and temperature are not of the water either
    if value is None:
        return "dry" if quantity == "ec" else "n.a"
    return f"{value:.{DECIMALS[quantity]}f}"
