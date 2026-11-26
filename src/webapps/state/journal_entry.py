"""A journal entry: one reading and its metadata. No UI and no file, so it is tested without a browser.

What a card shows, and the entry being measured. Every rule of what a journal entry needs, by its
reading_status, is here. How it is written to the csv is journal_entry_csv.py.
"""

from dataclasses import dataclass, replace
from datetime import datetime

from webapps.settings import BENCH, TIMEZONE

# the live values, by the name the pen gives them
METRICS = ("ph", "ec", "temperature")
# the reading_status values the app writes, of those the warehouse accepts. not unreliable, for now
MEASURED = "measured"
SKIPPED = "skipped"
# a live value not received from the pen yet, told apart from None, a value the pen has not got
NOT_RECEIVED = ""
# the most digits of an ml, the mask of its field: up to 9999, so staging's range test still judges it
ML_DIGITS = 4


@dataclass
class JournalEntry:
    """One reading at a spot of a room.

    - live values (ph, ec, temperature): NOT_RECEIVED until the pen sends one, None for one it has not got
    - ml, remarks: typed by the user. remarks is optional, empty for none
    - reading_status: measured, until the user skips it
    - date_time, device: stamped when it is confirmed
    """

    spot: str
    room: str = ""
    bench: str = BENCH
    date_time: datetime | None = None
    device: str = ""
    ph: float | str | None = NOT_RECEIVED
    ec: float | str | None = NOT_RECEIVED
    temperature: float | str | None = NOT_RECEIVED
    ml: int | None = None
    remarks: str = ""
    reading_status: str = MEASURED

    def is_ready(self) -> bool:
        """It has what it needs to be confirmed.

        - with a reading (measured): the ml and every live value, none of them n.a
        - without (skipped): nothing
        """
        if not self.has_reading():
            return True
        values = (getattr(self, metric) for metric in METRICS)
        return self.ml is not None and all(value not in (None, NOT_RECEIVED) for value in values)

    def is_typed(self) -> bool:
        """The user has typed something in it, which a move to another room would lose. Not the live values,
        which the pen sends again."""
        return self.ml is not None or self.remarks.strip() != ""

    def has_reading(self) -> bool:
        """It has a reading: ml and live values. Every reading_status but skipped."""
        return self.reading_status != SKIPPED

    def make_skipped(self) -> "JournalEntry":
        """A copy of it, skipped: no reading, so ready to be confirmed as it is. Its remarks kept."""
        return replace(self, reading_status=SKIPPED)

    def receive_live_value(self, metric: str, value: float | None) -> None:
        setattr(self, metric, value)

    def make_confirmed(self, device: str) -> "JournalEntry":
        """A copy of it as it is written: taken now by the device, keeping only what it holds once confirmed.

        A copy, so it is unchanged should the write fail.
        - a live value not received is one not got: None
        - without a reading (skipped): no device, no ml and no live values
        """
        confirmed = replace(self, date_time=datetime.now(TIMEZONE), device=device if self.has_reading() else "")
        for metric in METRICS:
            if getattr(confirmed, metric) == NOT_RECEIVED:
                setattr(confirmed, metric, None)
        if not confirmed.has_reading():
            confirmed.ml = None
            for metric in METRICS:
                setattr(confirmed, metric, None)
        return confirmed
