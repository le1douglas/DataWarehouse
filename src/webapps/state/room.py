"""The journal entries of a room, taken one after the other: no UI and no file, so it is tested without a browser."""

from webapps.state.journal_entry import JournalEntry
from webapps.state.journal_entry_state import JournalEntryState

# a bench and one of its spots: which journal entry of a room it is
type BenchSpot = tuple[str, str]


class Room:
    """The journal entries of the room named name: those confirmed, and the one being measured.

    - bench_spots: every bench and spot of the room, in the order they are taken, given by the walk
    - confirmed_entries: by bench and spot, given by the walk, which reads them from the csv
    - the current bench and spot is the first without a confirmed entry. a deleted one has none again, so
      it is taken again before going on
    - current_entry, of the current bench and spot, is the only thing not in the csv: a new one whenever
      they change, None when every one is confirmed
    """

    def __init__(
        self, name: str, bench_spots: tuple[BenchSpot, ...], confirmed_entries: dict[BenchSpot, JournalEntry]
    ) -> None:
        self.name = name
        self.bench_spots = bench_spots
        self.confirmed_entries: dict[BenchSpot, JournalEntry] = {}
        self.current_entry: JournalEntry | None = None
        self.set_confirmed_entries(confirmed_entries)

    def get_entry(self, bench_spot: BenchSpot) -> JournalEntry:
        """The entry of the bench and spot: confirmed, the current entry, or an empty one while it is pending."""
        if bench_spot in self.confirmed_entries:
            return self.confirmed_entries[bench_spot]
        if self._is_current(bench_spot):
            return self.current_entry
        return self._make_entry(bench_spot)

    def get_state(self, bench_spot: BenchSpot) -> JournalEntryState:
        if bench_spot in self.confirmed_entries:
            return JournalEntryState.CONFIRMED
        if self._is_current(bench_spot):
            return JournalEntryState.CURRENT
        return JournalEntryState.PENDING

    def set_confirmed_entries(self, confirmed_entries: dict[BenchSpot, JournalEntry]) -> None:
        """The confirmed entries, by bench and spot, and a new current entry when the current bench and spot
        change: after a confirm, or a delete before it. The current entry kept otherwise, with what is typed in
        it."""
        self.confirmed_entries = confirmed_entries
        current = next((bench_spot for bench_spot in self.bench_spots if bench_spot not in confirmed_entries), None)
        if current is None:
            self.current_entry = None
        elif not self._is_current(current):
            self.current_entry = self._make_entry(current)

    def is_complete(self) -> bool:
        """Every bench and spot is confirmed: there is no current entry."""
        return self.current_entry is None

    def receive_live_value(self, metric: str, value: float | None) -> None:
        """A live value of the pen, for the current entry. Ignored when every bench and spot is confirmed."""
        if self.current_entry is not None:
            self.current_entry.receive_live_value(metric, value)

    def _is_current(self, bench_spot: BenchSpot) -> bool:
        entry = self.current_entry
        return entry is not None and (entry.bench, entry.spot) == bench_spot

    def _make_entry(self, bench_spot: BenchSpot) -> JournalEntry:
        bench, spot = bench_spot
        return JournalEntry(spot, room=self.name, bench=bench)
