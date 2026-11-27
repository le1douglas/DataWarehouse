"""The walk through the rooms, such as the morning walk: no UI, so it is tested without a browser."""

from webapps.settings import WalkSettings
from webapps.state.journal_entry import AbsolutePosition, JournalEntry
from webapps.state.journal_entry_csv import JournalEntryCsv


class Walk:
    """Every journal entry of the walk, the open room, the selected entry, and every write of the csv.

    - entries: one per absolute position, in walk order: rooms in their order, in each every spot of a bench, then
      the next bench (WalkSettings). read from the csv when the walk is made, an empty one where it has none, then
      the source of truth: the csv is written from it after each confirm, skip and delete
    - a room is the entries with its name: there is no room object
    - open_room: the name of the room shown and worked on, set only by go_to_room
    - selected: the absolute position of the entry being measured, or None. set only by select: an unconfirmed
      entry of the open room
    - the pen is not its own: the page passes its values and its name
    """

    def __init__(self, settings: WalkSettings, journal: JournalEntryCsv) -> None:
        self.rooms = settings.rooms
        self.journal = journal
        confirmed = journal.read_entries()
        self.entries: dict[AbsolutePosition, JournalEntry] = {}
        for room in settings.rooms:
            for bench in settings.benches:
                for spot in settings.spots:
                    position = (room, bench, spot)
                    self.entries[position] = confirmed.get(position) or JournalEntry(spot, room=room, bench=bench)
        self.open_room = ""
        self.selected: AbsolutePosition | None = None
        # the first room of the list, for now
        self.go_to_room(self.rooms[0])

    def get_entries(self, room: str) -> list[JournalEntry]:
        """The entries of the room, in walk order."""
        return [entry for entry in self.entries.values() if entry.room == room]

    def get_selected_entry(self) -> JournalEntry | None:
        return None if self.selected is None else self.entries[self.selected]

    def select(self, position: AbsolutePosition | None) -> None:
        """Selects the entry at the position, or none. The only place the selection is set.

        - an entry must be unconfirmed and of the open room: a confirmed one is only deleted
        - the entry deselected, when unconfirmed, loses its live values: only the selected entry holds the pen's
        """
        if position is not None:
            entry = self.entries[position]
            if entry.is_confirmed() or entry.room != self.open_room:
                raise ValueError(f"{position} is confirmed or not in room {self.open_room}")
        deselected = self.get_selected_entry()
        # confirmed: its values are its reading, kept
        if position != self.selected and deselected is not None and not deselected.is_confirmed():
            deselected.clear_live_values()
        self.selected = position

    def find_selectable(self, step: int) -> AbsolutePosition | None:
        """The nearest unconfirmed entry of the open room from the selected one, stepping through the room in walk
        order: 1 the next, -1 the one before, 2 the next in the same column of two. None when there is none or
        nothing is selected: the steps stop at the edge of the room."""
        if self.selected is None:
            return None
        entries = self.get_entries(self.open_room)
        index = next(i for i, entry in enumerate(entries) if entry.get_absolute_position() == self.selected)
        end = len(entries) if step > 0 else -1
        ahead = (entries[i] for i in range(index + step, end, step))
        return next((entry.get_absolute_position() for entry in ahead if not entry.is_confirmed()), None)

    def go_to_room(self, name: str) -> None:
        """Opens the room and selects its first unconfirmed entry, none when it is complete. What is typed in its
        entries, and in those of every other room, is kept."""
        self.open_room = name
        self.select(self._find_first_unconfirmed(name))

    def is_complete(self) -> bool:
        """Every entry of every room is confirmed."""
        return all(entry.is_confirmed() for entry in self.entries.values())

    def get_room_index(self) -> int:
        """The place of the open room in the walk, 0 for the first."""
        return self.rooms.index(self.open_room)

    def receive_live_value(self, metric: str, value: float | None) -> None:
        """A live value of the pen, for the selected entry. Dropped when none is selected."""
        entry = self.get_selected_entry()
        if entry is not None:
            entry.receive_live_value(metric, value)

    def is_confirm_allowed(self) -> bool:
        """The selected entry is ready."""
        entry = self.get_selected_entry()
        return entry is not None and entry.is_ready()

    def confirm(self, device: str) -> None:
        """Confirms the selected entry as taken by the device, then selects the next."""
        entry = self.get_selected_entry()
        if entry is None or not entry.is_ready():
            raise ValueError("the selected entry is not ready to be confirmed")
        self._write(entry.make_confirmed(device))
        self._select_next()

    def skip(self) -> None:
        """Confirms the selected entry as skipped: no pen needed, its remarks kept. Then selects the next."""
        entry = self.get_selected_entry()
        if entry is None:
            raise ValueError("no entry is selected")
        self._write(entry.make_skipped().make_confirmed(""))
        self._select_next()

    def delete(self, position: AbsolutePosition) -> None:
        """Empties the confirmed entry at the position, of the open room, and selects it."""
        entry = self.entries[position]
        if not entry.is_confirmed():
            raise ValueError(f"{position} is not confirmed")
        room, bench, spot = position
        self._write(JournalEntry(spot, room=room, bench=bench))
        self.select(position)

    def read_csv_text(self) -> str:
        """The csv as it is on disk, every room."""
        return self.journal.read_text()

    def _write(self, entry: JournalEntry) -> None:
        """Puts the entry in the list in place of the one at its position, then writes the csv again from the
        list."""
        self.entries[entry.get_absolute_position()] = entry
        self.journal.write_entries(self.entries.values())

    def _select_next(self) -> None:
        """The first unconfirmed entry of the open room. When it is complete, the next room is opened, the last
        room excepted: nothing selected then."""
        position = self._find_first_unconfirmed(self.open_room)
        index = self.get_room_index() + 1
        if position is None and index < len(self.rooms):
            self.go_to_room(self.rooms[index])
        else:
            self.select(position)

    def _find_first_unconfirmed(self, room: str) -> AbsolutePosition | None:
        """The absolute position of the first unconfirmed entry of the room, in walk order. None when complete."""
        entry = next((entry for entry in self.get_entries(room) if not entry.is_confirmed()), None)
        return None if entry is None else entry.get_absolute_position()
