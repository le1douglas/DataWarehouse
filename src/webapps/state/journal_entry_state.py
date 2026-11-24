"""Where a journal entry is in its room's round: it decides how its card looks. Not its reading_status."""

from enum import StrEnum


class JournalEntryState(StrEnum):
    """Derived by the room from the csv and the order of the spots, never stored.

    - pending: its spot is not reached yet
    - current: its spot is being measured
    - confirmed: it has its row in the csv
    """

    PENDING = "pending"
    CURRENT = "current"
    CONFIRMED = "confirmed"
