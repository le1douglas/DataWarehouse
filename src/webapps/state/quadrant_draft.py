"""The draft of the current quadrant: no UI, so it is tested without a browser, and nothing of the csv."""

from dataclasses import dataclass

# the live values, by the name the pen gives them
QUANTITIES = ("ph", "ec", "temperature")
# a value not received from the pen yet, told apart from None, a value the pen has not got
NOT_RECEIVED = ""
# the most digits of an ml, the mask of its field: up to 9999, so staging's range test still judges it
ML_DIGITS = 4


@dataclass
class QuadrantDraft:
    """The journal entry being taken at the current spot, until it is confirmed.

    The live values of the pen, received since the spot became the current one, and the ml and remarks
    typed: nowhere else until confirmed. The live values are taken as the pen sends them: NOT_RECEIVED
    until it sends one, and None for one it has not got.
    """

    spot: str
    ph: float | str | None = NOT_RECEIVED
    ec: float | str | None = NOT_RECEIVED
    temperature: float | str | None = NOT_RECEIVED
    ml: int | None = None
    # free text of the grower, such as no runoff. optional: empty for none
    remarks: str = ""

    @property
    def values(self) -> dict[str, float | str | None]:
        """The live values, by quantity."""
        return {quantity: getattr(self, quantity) for quantity in QUANTITIES}

    @property
    def ready(self) -> bool:
        """It has what its journal entry needs: the ml and every live value, None included, as the pen sent it."""
        received = all(getattr(self, quantity) != NOT_RECEIVED for quantity in QUANTITIES)
        return self.ml is not None and received

    def set_live(self, quantity: str, value: float | None) -> None:
        setattr(self, quantity, value)

    def forget_live(self) -> None:
        """Forgets the live values, so none of a pen that is gone is kept."""
        for quantity in QUANTITIES:
            setattr(self, quantity, NOT_RECEIVED)
