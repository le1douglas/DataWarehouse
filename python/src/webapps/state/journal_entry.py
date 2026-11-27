"""A journal entry: one reading and its metadata. No UI and no file, so it is tested without a browser.

One per absolute position of the walk, filled in any order: what its card shows and what the csv writes. It is the
same entry before and after it is confirmed, only stamped. Every rule of what a journal entry needs, by its
reading_status, is here. How it is written to the csv is journal_entry_csv.py.
"""

from dataclasses import dataclass, replace
from datetime import datetime

from webapps.settings import TIMEZONE

# the live values, by the name the pen gives them
METRICS = ("ph", "ec", "temperature")
# the reading_status values the app writes, of those the warehouse accepts. not unreliable, for now
MEASURED = "measured"
SKIPPED = "skipped"
# the reading_status of an entry not confirmed yet: never written, as the csv holds only confirmed entries
IN_PROGRESS = "in_progress"
# a live value not received from the pen yet, told apart from None, a value the pen has not got
NOT_RECEIVED = ""
# the most digits of an ml, the mask of its field: up to 9999, so staging's range test still judges it
ML_DIGITS = 4

# room, bench and spot: which journal entry of the walk it is
type AbsolutePosition = tuple[str, str, str]


@dataclass
class JournalEntry:
    """One reading at a spot of a room.

    - live values (ph, ec, temperature): NOT_RECEIVED until the pen sends one, None for one it has not got
    - ml, remarks: typed by the user. remarks is optional, empty for none
    - reading_status: in_progress, until it is confirmed (measured) or skipped
    - date_time, device: stamped when it is confirmed or skipped, with its reading_status
    - confirmed: its reading_status is not in_progress. measured or skipped
    """

    spot: str
    room: str = ""
    bench: str = ""
    date_time: datetime | None = None
    device: str = ""
    ph: float | str | None = NOT_RECEIVED
    ec: float | str | None = NOT_RECEIVED
    temperature: float | str | None = NOT_RECEIVED
    ml: int | None = None
    remarks: str = ""
    reading_status: str = IN_PROGRESS

    def is_confirmed(self) -> bool:
        """It is confirmed or skipped: its reading_status is not in_progress."""
        return self.reading_status != IN_PROGRESS

    def get_absolute_position(self) -> AbsolutePosition:
        return (self.room, self.bench, self.spot)

    def is_ready(self) -> bool:
        """It has what it needs to be confirmed.

        - with a reading (in_progress): the ml and every live value, none of them n.a
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
        """It has a reading: ml and live values. Every reading_status but skipped, in_progress too."""
        return self.reading_status != SKIPPED

    def make_skipped(self) -> "JournalEntry":
        """A copy of it, skipped, as it is written: stamped now, its remarks kept.

        A copy, so it is unchanged should the write fail.
        - no reading: no device, no ml and no live values
        """
        skipped = replace(self, reading_status=SKIPPED, date_time=datetime.now(TIMEZONE), device="", ml=None)
        for metric in METRICS:
            setattr(skipped, metric, None)
        return skipped

    def receive_live_value(self, metric: str, value: float | None) -> None:
        setattr(self, metric, value)

    def clear_live_values(self) -> None:
        """Every live value back to not received, as before the pen sent any."""
        for metric in METRICS:
            setattr(self, metric, NOT_RECEIVED)

    def make_confirmed(self, device: str) -> "JournalEntry":
        """A copy of it, measured, as it is written: taken now by the device.

        A copy, so it is unchanged should the write fail.
        - a live value not received is one not got: None
        """
        confirmed = replace(self, reading_status=MEASURED, date_time=datetime.now(TIMEZONE), device=device)
        for metric in METRICS:
            if getattr(confirmed, metric) == NOT_RECEIVED:
                setattr(confirmed, metric, None)
        return confirmed
