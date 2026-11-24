"""The state of a quadrant, and the csv row (journal_csv.py) it becomes: no UI, so it is tested without a browser."""

import os
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from webapps.state.journal_csv import CSV_COLUMNS

# the live values, by the name the pen gives them, with their decimals in the csv
DECIMALS = {"ph": 2, "ec": 2, "temperature": 1}
# a value not received from the pen yet, told apart from None, a value the pen has not got
NOT_RECEIVED = ""
# a value not taken, in the csv. never an empty string, so staging tells it from a value lost on the way
NOT_AVAILABLE = "n.a"
# below this ml a journal entry is unreliable, else measured. the same as unreliable_reading_max_ml in
# DataWarehouseDbt/dbt_project.yml: change both together
UNRELIABLE_READING_MAX_ML = 300
# the most digits of an ml, the mask of its field: up to 9999, so staging's range test still judges it
ML_DIGITS = 4
# every journal entry is taken at this bench for now, as in bluelab_datastreamer/drip_drain.py
BENCH = "4"
# read here, not from the container's clock, which falls back to UTC silently: an empty or unknown TZ stops the app
TIMEZONE = ZoneInfo(os.environ["TZ"])


@dataclass
class QuadrantState:
    """What a quadrant shows of its spot: the journal entry being taken, or a copy of the one confirmed.

    Being taken, it has the live values of the pen and the ml and remarks typed, which are nowhere else. Confirmed
    when the csv has its row, it has a copy of the values of that row, which only load changes: the csv
    stays their only record. The live values are NOT_RECEIVED until the pen sends one, and
    None for one the pen has not got, such as ec with the probe dry.
    """

    spot: str
    ph: float | str | None = NOT_RECEIVED
    ec: float | str | None = NOT_RECEIVED
    temperature: float | str | None = NOT_RECEIVED
    ml: int | None = None
    # free text of the grower, such as no runoff. optional: empty for none
    remarks: str = ""
    confirmed: bool = False

    @property
    def csv_spot(self) -> str:
        # Drip Left becomes drip_left
        return self.spot.lower().replace(" ", "_")

    @property
    def ready(self) -> bool:
        """It has what its row needs: the ml and every live value, None included, as the pen sent it."""
        received = all(getattr(self, quantity) != NOT_RECEIVED for quantity in DECIMALS)
        return not self.confirmed and self.ml is not None and received

    def set_live(self, quantity: str, value: float | None) -> None:
        """A live value of the pen, ignored once confirmed."""
        if not self.confirmed:
            setattr(self, quantity, value)

    def forget_live(self) -> None:
        """Forgets the live values, unless confirmed, so none of another spot or of a pen that is gone is kept."""
        if not self.confirmed:
            for quantity in DECIMALS:
                setattr(self, quantity, NOT_RECEIVED)

    def to_row(self, device: str) -> dict:
        """The row of the csv, taken now. room stays empty for now."""
        ml = int(self.ml)
        row = dict.fromkeys(CSV_COLUMNS, "")
        row.update(
            date_time=datetime.now(TIMEZONE).replace(tzinfo=None).isoformat(timespec="microseconds"),
            device=device,
            spot=self.csv_spot,
            ml=str(ml),
            bench=BENCH,
            # only spaces is none
            remarks=self.remarks.strip(),
            reading_status="unreliable" if ml < UNRELIABLE_READING_MAX_ML else "measured",
        )
        for quantity, decimals in DECIMALS.items():
            value = getattr(self, quantity)
            # a dry probe has no ec, and its ph and temperature are not of the water either
            taken = self.ec is not None and value not in (None, NOT_RECEIVED)
            row[quantity] = f"{value:.{decimals}f}" if taken else NOT_AVAILABLE
        return row

    def load(self, row: dict | None) -> None:
        """What the csv says of the spot: confirmed with the values of its row, or not confirmed without one.

        Without a row, a quadrant state being taken keeps what it has, and a confirmed one, whose row was
        deleted, starts again from nothing.
        """
        if row is not None:
            for quantity in DECIMALS:
                setattr(self, quantity, None if row[quantity] == NOT_AVAILABLE else float(row[quantity]))
            self.ml = int(row["ml"])
            self.remarks = row["remarks"]
            self.confirmed = True
        elif self.confirmed:
            self.confirmed = False
            self.forget_live()
            self.ml = None
            self.remarks = ""
