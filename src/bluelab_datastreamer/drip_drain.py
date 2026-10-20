"""Back end of the drip and drain readings: the rooms, the room being taken, and the csv they are written to.

Prints nothing and reads no key: a reading that cannot be taken comes back as the reason, a csv
that cannot be used as an exception. Only the standard library.
"""

import csv
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

CSV_PATH = Path(__file__).with_name("drip_drain.csv")
CSV_COLUMNS = (
    "date_time",
    "subject",
    "notes",
    "type",
    "ec",
    "ec_pore",
    "ec_bulk",
    "ph",
    "mc",
    "temp",
    "device",
    "media",
    "tags",
)
# the rooms of each part of the day, in the order they are taken
ROOMS = {
    "morning": ("1.30", "1.29", "1.28", "1.27", "1.26", "1.25", "1.24", "0.31", "0.32", "0.33"),
    "afternoon": ("1.23", "1.22", "1.21", "1.20", "1.19", "1.18", "1.17", "0.27", "0.28", "0.29"),
}
# once every room of the part of the day is done, the csv is moved to this folder, named by the
# date and the number of the part of the day, such as 261020-1.csv. the path in the container, where
# compose mounts the windows folder DAILY_RAW_CSV_DIR of .env
DEFAULT_DAILY_DIR = Path("/daily_raw_csv")
PART_NUMBERS = {"morning": 1, "afternoon": 2}
READINGS_PER_ROOM = 4
# the lines of a room, in the order they are taken
LINE_NAMES = ("Drip Left", "Drip Right", "Drain Left", "Drain Right")


def csv_values(ec: float | None, ph: float | None, temperature: float | None) -> dict:
    """The values as the csv stores them, an empty string for none."""
    # a dry probe has no ec, and its ph and temperature are not of the water either
    if ec is None:
        return {"ec": "", "ph": "", "temp": ""}
    return {
        "ec": f"{ec:.2f}",
        "ph": "" if ph is None else f"{ph:.2f}",
        "temp": "" if temperature is None else f"{temperature:.1f}",
    }


NO_VALUES = csv_values(None, None, None)


@dataclass
class Room:
    """The room being taken: the ml typed first, then the readings recorded, one per line.

    Typing goes to the ml of the line the arrows are on, a reading to its reading. When every line
    of one is filled, the next empty line of the other is taken, and when every line has both, the
    confirmation, one past the last line. Once confirmed, the room cannot be changed.
    """

    name: str
    lines: int
    # an empty string for a line without ml, None for a line without a reading
    ml: list[str] = field(init=False)
    readings: list[dict | None] = field(init=False)
    # the line the arrows are on. one past the last line is the confirmation, which can be gone to
    # only when the room is complete
    line: int = 0
    typing_ml: bool = True
    # true once the room is confirmed, while it is written to the csv
    saving: bool = False

    def __post_init__(self) -> None:
        self.ml = [""] * self.lines
        self.readings = [None] * self.lines

    @property
    def complete(self) -> bool:
        return all(self.ml) and all(self.readings)

    @property
    def confirming(self) -> bool:
        return self.line == self.lines

    @property
    def started(self) -> bool:
        return any(self.ml) or any(self.readings)

    @property
    def line_names(self) -> tuple[str, ...]:
        # a room continued from the csv has only its last lines left
        return LINE_NAMES[READINGS_PER_ROOM - self.lines :]

    def move(self, step: int) -> None:
        """Goes step lines down, up when negative, and to the confirmation only when the room is complete."""
        last = self.lines if self.complete else self.lines - 1
        self.line = max(0, min(last, self.line + step))

    def switch(self, to_ml: bool) -> None:
        """Goes from the readings to the ml or back, on the same line."""
        self.typing_ml = to_ml

    def type_digit(self, digit: str) -> None:
        self.ml[self.line] += digit

    def next_line(self) -> None:
        """Goes on from a line whose ml is typed."""
        if self.ml[self.line]:
            self._advance(self.ml)

    def delete(self) -> None:
        """Removes a digit of the ml or the reading of the line. On a line without one, goes back to the one before."""
        if self.confirming:
            self.line -= 1
            return
        if self.typing_ml and self.ml[self.line]:
            self.ml[self.line] = self.ml[self.line][:-1]
        elif not self.typing_ml and self.readings[self.line] is not None:
            self.readings[self.line] = None
        elif self.line > 0:
            # back to the line before, to correct it
            self.line -= 1

    def record(self, date_time: str, ec: float | None, ph: float | None, temperature: float | None) -> str | None:
        """Puts a reading in the line the arrows are on and goes on. Why it cannot when it cannot, else None."""
        if self.typing_ml:
            return "press right to measure"
        if self.saving:
            return "the room is being written to the csv"
        if self.confirming:
            return "the room is complete. confirm it, or go up to change it"
        if self.readings[self.line] is not None:
            return "the line has one already. delete it first"
        self.readings[self.line] = {"date_time": date_time, **csv_values(ec, ph, temperature)}
        self._advance(self.readings)
        return None

    def confirm(self) -> None:
        self.saving = True

    def rows(self, pen_name: str) -> list[dict]:
        """The room as rows of the csv, in the shape of a journal entries export."""
        rows = []
        for ml, reading in zip(self.ml, self.readings):
            row = dict.fromkeys(CSV_COLUMNS, "")
            row.update(
                subject=f"{pen_name} - Measurement",
                notes=str(int(ml)),
                type="measurement",
                tags=self.name,
                **reading,
            )
            rows.append(row)
        return rows

    def _advance(self, values: list) -> None:
        """After a line is filled: goes to the next empty line of values.

        When every line of values is filled, goes to the other mode, and when every line has both its
        ml and its reading, to the confirmation.
        """
        following = next_empty(values, self.line)
        if following is not None:
            self.line = following
            return
        following = next_empty(self.readings if self.typing_ml else self.ml, 0)
        if following is None:
            self.line = self.lines
            return
        self.typing_ml = not self.typing_ml
        self.line = following


def next_empty(values: list, start: int) -> int | None:
    """The first empty line from start on, going round to the top. None when every line is filled."""
    for offset in range(len(values)):
        index = (start + offset) % len(values)
        if not values[index]:
            return index
    return None


def read_csv() -> list[dict]:
    """The rows of the csv, without empty lines. Creates the csv with its header if it is missing or empty."""
    if not CSV_PATH.exists() or not CSV_PATH.read_text().strip():
        CSV_PATH.write_text(",".join(CSV_COLUMNS) + "\n")
    with CSV_PATH.open(newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError(f"the header of {CSV_PATH.name} is not {','.join(CSV_COLUMNS)}")
        return [row for row in reader if any((cell or "").strip() for cell in row.values())]


def next_room(rows: list[dict], part_of_day: str) -> Room | None:
    """The room of the part of the day that continues from the last row, with the lines it still needs.

    None when every room is done. Every row must be of the part of the day: a csv of the other one
    is not continued.
    """
    rooms = ROOMS[part_of_day]
    others = sorted({row["tags"] for row in rows} - set(rooms))
    if others:
        raise ValueError(
            f"{CSV_PATH.name} has rows with tags {', '.join(others)}, which are not rooms of this part of the day"
        )
    if not rows:
        return Room(rooms[0], READINGS_PER_ROOM)
    last = rows[-1]["tags"]
    index = rooms.index(last)
    # the rows of the last room are the ones at the end with its tags
    in_room = 0
    for row in reversed(rows):
        if row["tags"] != last:
            break
        in_room += 1
    if in_room < READINGS_PER_ROOM:
        return Room(rooms[index], READINGS_PER_ROOM - in_room)
    return Room(rooms[index + 1], READINGS_PER_ROOM) if index + 1 < len(rooms) else None


def append_rows(rows: list[dict]) -> None:
    """Appends the rows to the csv. A PermissionError while the csv is open in another program."""
    # a hand edit can leave empty lines (blank, or only commas when excel empties a row) at the end,
    # or no newline after the last row, so they are removed before the rows are appended
    content = CSV_PATH.read_text()
    lines = content.splitlines()
    while len(lines) > 1 and not lines[-1].strip(" ,\t"):
        lines.pop()
    tidy = "\n".join(lines) + "\n"
    if tidy != content:
        CSV_PATH.write_text(tidy)
    with CSV_PATH.open("a", newline="") as file:
        csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n").writerows(rows)


def archive_csv(daily_dir: Path, part_of_day: str) -> Path:
    """Copies the csv to the daily folder and leaves it with its header only. Never overwrites a file there."""
    target = daily_dir / f"{datetime.now():%y%m%d}-{PART_NUMBERS[part_of_day]}.csv"
    if target.exists():
        raise FileExistsError(f"{target} exists already")
    shutil.copyfile(CSV_PATH, target)
    CSV_PATH.write_text(",".join(CSV_COLUMNS) + "\n")
    return target
