"""The walk through the rooms, such as the morning walk: no UI, so it is tested without a browser."""

from webapps.settings import WalkSettings
from webapps.state.journal_entry import AbsolutePosition, JournalEntry
from webapps.state.journal_entry_csv import JournalEntryCsv

# the step of each direction through the open room, by the grid of two columns: left and right in walk order, up
# and down in the same column. one column, on a narrow screen, is not followed: a keyboard means a wide one
DIRECTION_STEPS = {"left": -1, "right": 1, "up": -2, "down": 2}


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
        if position is not None and not self._is_selectable(self.entries[position]):
            raise ValueError(f"{position} is confirmed or not in room {self.open_room}")
        deselected = self.get_selected_entry()
        # confirmed: its values are its reading, kept
        if position != self.selected and deselected is not None and not deselected.is_confirmed():
            deselected.clear_live_values()
        self.selected = position

    def move(self, direction: str) -> bool:
        """Selects the nearest selectable entry in the direction from the selected one, as a tap would. True when
        the selection moved: none there, or nothing selected, and nothing changes.
        - left and right go round the room: past the last entry, the first
        - up and down stop at its edge: going round would change column"""
        if self.selected is None:
            return False
        step = DIRECTION_STEPS[direction]
        position = self._find_selectable(self._get_selected_index(), step, wrap=abs(step) == 1)
        if position is None:
            return False
        self.select(position)
        return True

    def go_to_room(self, name: str) -> None:
        """Opens the room and selects its first unconfirmed entry, none when it is complete. What is typed in its
        entries, and in those of every other room, is kept."""
        self.open_room = name
        self.select(self._find_selectable(-1, 1, wrap=False))

    def has_room(self, step: int) -> bool:
        """There is a room step rooms from the open one: -1 the one before, 1 the next. The rooms stop at the
        first and the last."""
        return 0 <= self.get_room_index() + step < len(self.rooms)

    def move_room(self, step: int) -> bool:
        """Opens the room step rooms from the open one, as go_to_room. True when it moved: none there, and nothing
        changes."""
        if not self.has_room(step):
            return False
        self.go_to_room(self.rooms[self.get_room_index() + step])
        return True

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
        self._write(entry.make_skipped())
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
        """The next unconfirmed entry of the open room after the one just confirmed, round the room as the right
        arrow goes. When it is complete, the next room is opened, the last room excepted: nothing selected then."""
        position = self._find_selectable(self._get_selected_index(), 1, wrap=True)
        if position is None and self.move_room(1):
            return
        self.select(position)

    def _get_selected_index(self) -> int:
        """The place of the selected entry in the open room, 0 for the first. Only called with one selected."""
        positions = [entry.get_absolute_position() for entry in self.get_entries(self.open_room)]
        return positions.index(self.selected)

    def _is_selectable(self, entry: JournalEntry) -> bool:
        """Unconfirmed and of the open room: a confirmed entry is only deleted."""
        return not entry.is_confirmed() and entry.room == self.open_room

    def _find_selectable(self, start: int, step: int, wrap: bool) -> AbsolutePosition | None:
        """The first selectable entry of the open room after the index start, stepping by step in walk order: 1
        the next, -1 the one before, 2 the next in the same column of two. Every search of the selection.
        - start -1, step 1, no wrap: the first selectable entry of the room
        - wrap: round the room, past the last entry the first, the start itself left out
        - no wrap: stops at the edge of the room
        None when there is none."""
        entries = self.get_entries(self.open_room)
        if wrap:
            indexes = [(start + step * offset) % len(entries) for offset in range(1, len(entries))]
        else:
            end = len(entries) if step > 0 else -1
            indexes = list(range(start + step, end, step))
        ahead = (entries[i] for i in indexes)
        return next((entry.get_absolute_position() for entry in ahead if self._is_selectable(entry)), None)
