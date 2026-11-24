"""One quadrant of the drip and drain page: a spot as a card."""

from collections.abc import Callable
from typing import Any

from nicegui import ui

from webapps.state.journal_csv import DECIMALS
from webapps.state.quadrant_draft import ML_DIGITS, NOT_RECEIVED, QuadrantDraft

# the live values shown, by the name the pen gives them, with their decimals as the csv writes them (DECIMALS)
LABELS = {"ph": "pH", "ec": "EC", "temperature": "Temp"}
# the look of the card: CURRENT while it is being taken, CONFIRMED once it has its row
CURRENT = "ring-4 ring-blue-500"
CONFIRMED = "bg-green-1"


class Quadrant(ui.card):
    """A spot as a card, drawn again by the page whenever the csv changes.

    Every card has the same parts in the same place: the live values, the ml, the remarks and a button.
    Only what is in them differs, and the colour of the card:
    - confirmed, with its row: the text of the row as the csv has it, read only, and Delete (on_delete)
    - current, with the draft: bound to it, so the live values and the typing show by themselves, and
      Confirm, or Enter in a field (on_confirm), enabled while can_confirm says so
    - not reached yet, with neither: empty, disabled
    """

    def __init__(
        self,
        spot: str,
        row: dict | None,
        draft: QuadrantDraft | None,
        can_confirm: Callable[[], bool],
        on_confirm: Callable[[], Any],
        on_delete: Callable[[], Any],
    ) -> None:
        super().__init__()
        self._can_confirm = can_confirm
        self.classes("w-full")
        with self:
            ui.label(spot).classes("text-lg font-bold")
            # side by side: the labels in a row, the values in a row under them
            with ui.grid(columns=len(LABELS)).classes("w-full text-center gap-y-0"):
                for label in LABELS.values():
                    ui.label(label).classes("text-grey-7")
                values = {quantity: ui.label("–").classes("font-mono text-lg") for quantity in LABELS}
            # text with a mask of digits, not ui.number: a number field takes e, + and -, and reads 4e2 as 400
            # - inputmode: the number pad on a phone
            ml = ui.input("ml").classes("w-full").props(f'mask="{"#" * ML_DIGITS}" inputmode=numeric')
            remarks = ui.input("remarks (optional)").classes("w-full")
            # the button last, so it is in the same place on every card
            if row is not None:
                self.classes(CONFIRMED)
                for quantity, value in values.items():
                    value.set_text(row[quantity])
                ml.value = row["ml"]
                remarks.value = row["remarks"]
                # read only, not disabled: shown as clearly as when it was typed
                ml.props("readonly")
                remarks.props("readonly")
                ui.button("Delete", icon="delete", color="negative", on_click=on_delete).classes("w-full")
            elif draft is not None:
                self.classes(CURRENT)
                for quantity, value in values.items():
                    value.bind_text_from(draft, quantity, backward=lambda v, q=quantity: shown(q, v))
                # autofocus: the focus in it whenever the card is drawn, so the ml is typed straight away
                ml.props("autofocus")
                ml.bind_value(draft, "ml", forward=lambda text: int(text) if text else None, backward=ml_text)
                remarks.bind_value(draft, "remarks")
                for field in (ml, remarks):
                    field.on("keydown.enter", on_confirm)
                confirm = ui.button("Confirm", icon="check", on_click=on_confirm).classes("w-full")
                confirm.bind_enabled_from(self, "can_confirm")
            else:
                ml.disable()
                remarks.disable()
                ui.button("Confirm", icon="check").classes("w-full").disable()

    @property
    def can_confirm(self) -> bool:
        return self._can_confirm()


def ml_text(ml: int | None) -> str:
    """The ml as the field shows it, empty for none."""
    return "" if ml is None else str(ml)


def shown(quantity: str, value: float | str | None) -> str:
    """A live value as the card shows it: n.a for one the pen has not got, as the csv writes it."""
    if value == NOT_RECEIVED:
        return "–"
    if value is None:
        return "n.a"
    return f"{value:.{DECIMALS[quantity]}f}"
