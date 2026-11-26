"""The daily walk through the rooms: no UI, so it is tested without a browser."""

from webapps.state.journal_entry import JournalEntry
from webapps.state.journal_entry_csv import JournalEntryCsv
from webapps.state.room import Room


class DailyWalk:
    """The rooms walked in their order, the one open, and every read and write of the csv.

    - room: the open room, read from the csv when it is opened and after each confirm and delete.
      replaced only here, so whoever holds the walk always reaches the open room
    - a confirm or skip that completes the room opens the next one, the last room excepted. only then:
      a complete room moved to by hand stays open, so its entries can be seen and deleted
    - the pen is not its own: the page passes its name
    """

    def __init__(self, rooms: tuple[str, ...], journal: JournalEntryCsv) -> None:
        self.rooms = rooms
        self.journal = journal
        # the first room of the list, for now
        self.room = self._open_room(rooms[0])

    def has_typed_entry(self) -> bool:
        """The current entry of the open room has something typed, which a move to another room would lose."""
        entry = self.room.current_entry
        return entry is not None and entry.is_typed()

    def go_to_room(self, name: str) -> None:
        """Opens the room: its confirmed entries from the csv, and a new current entry, so a typed one is lost."""
        self.room = self._open_room(name)

    def receive_live_value(self, metric: str, value: float | None) -> None:
        """A live value of the pen, for the open room."""
        self.room.receive_live_value(metric, value)

    def is_confirm_allowed(self) -> bool:
        """The current entry is ready."""
        entry = self.room.current_entry
        return entry is not None and entry.is_ready()

    def confirm(self, device: str) -> None:
        """Confirms the current entry as taken by the device: appends its row and reads the room again."""
        entry = self.room.current_entry
        if entry is None or not entry.is_ready():
            raise ValueError("the current entry is not ready to be confirmed")
        self._write(entry.make_confirmed(device))

    def skip(self) -> None:
        """Confirms the current entry as skipped: no pen needed, its remarks kept."""
        entry = self.room.current_entry
        if entry is None:
            raise ValueError("every spot of the room is confirmed")
        self._write(entry.make_skipped().make_confirmed(""))

    def delete(self, spot: str) -> None:
        """Removes the row of the spot of the open room, and reads the room again."""
        self.journal.delete(self.room.name, spot)
        self._read_room()

    def read_csv_text(self) -> str:
        """The csv as it is on disk, every room."""
        return self.journal.read_text()

    def _write(self, confirmed: JournalEntry) -> None:
        """Appends the row, then reads the room again: the current entry replaced only once it is written. The
        next room once this one is complete."""
        self.journal.append(confirmed)
        self._read_room()
        if self.room.is_complete():
            self._go_to_next_room()

    def _go_to_next_room(self) -> None:
        """The room after the open one, none after the last."""
        index = self.rooms.index(self.room.name) + 1
        if index < len(self.rooms):
            self.go_to_room(self.rooms[index])

    def _open_room(self, name: str) -> Room:
        return Room(name, self.journal.read_entries(name))

    def _read_room(self) -> None:
        self.room.set_confirmed_entries(self.journal.read_entries(self.room.name))
