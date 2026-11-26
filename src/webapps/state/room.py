"""The four spots of a room, taken one after the other: no UI and no file, so it is tested without a browser."""

from webapps.state.journal_entry import JournalEntry
from webapps.state.journal_entry_state import JournalEntryState

# the spots of a room in the order they are taken, as the csv writes them
SPOTS = ("drip_left", "drip_right", "drain_left", "drain_right")


class Room:
    """The journal entries of the room named name: those confirmed, and the one being measured.

    - confirmed_entries: given by the daily walk, which reads them from the csv
    - the current spot is the first without a confirmed entry, in the order of SPOTS. a deleted spot
      has none again, so it is taken again before going on
    - current_entry, of the current spot, is the only thing not in the csv: a new one whenever the
      current spot changes, None when every spot is confirmed
    """

    def __init__(self, name: str, confirmed_entries: dict[str, JournalEntry]) -> None:
        self.name = name
        self.confirmed_entries: dict[str, JournalEntry] = {}
        self.current_entry: JournalEntry | None = None
        self.set_confirmed_entries(confirmed_entries)

    def get_entry(self, spot: str) -> JournalEntry:
        """The entry of the spot: confirmed, the current entry, or an empty one while it is pending."""
        if spot in self.confirmed_entries:
            return self.confirmed_entries[spot]
        if self.current_entry is not None and self.current_entry.spot == spot:
            return self.current_entry
        return JournalEntry(spot, room=self.name)

    def get_state(self, spot: str) -> JournalEntryState:
        if spot in self.confirmed_entries:
            return JournalEntryState.CONFIRMED
        if self.current_entry is not None and self.current_entry.spot == spot:
            return JournalEntryState.CURRENT
        return JournalEntryState.PENDING

    def set_confirmed_entries(self, confirmed_entries: dict[str, JournalEntry]) -> None:
        """The confirmed entries, by spot, and a new current entry when the current spot changes: after a
        confirm, or a delete before it. The current entry kept otherwise, with what is typed in it."""
        self.confirmed_entries = confirmed_entries
        spot = next((spot for spot in SPOTS if spot not in confirmed_entries), None)
        if spot is None:
            self.current_entry = None
        elif self.current_entry is None or self.current_entry.spot != spot:
            self.current_entry = JournalEntry(spot, room=self.name)

    def receive_live_value(self, metric: str, value: float | None) -> None:
        """A live value of the pen, for the current entry. Ignored when every spot is confirmed."""
        if self.current_entry is not None:
            self.current_entry.receive_live_value(metric, value)
