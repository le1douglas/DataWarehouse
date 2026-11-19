"""Back end of the drip and drain readings: the rooms, the room being taken, and the csv they are written to.

Prints nothing and reads no key: a reading that cannot be taken comes back as the reason, a csv
that cannot be used as an exception. Only the standard library.
"""

import csv
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# the rooms done so far, until the part of the day is done
# - in the work-in-progress volume, so it survives the container
# - the subfolder is named only here, and made when it is missing
CSV_PATH = Path(os.environ["WORK_IN_PROGRESS_MOUNT"]) / "journal_entries" / "drip_drain.csv"
# the columns of dw_bronze.brnz_journal_entries (Database/01_create_schemas_and_tables.sql), the file the warehouse
# loads. stg_journal_entries judges them
CSV_COLUMNS = (
    "date_time",
    "device",
    "spot",
    "ml",
    "ec",
    "ph",
    "temperature",
    "room",
    "bench",
    "remarks",
    "reading_status",
)
# a value not taken, never an empty string, so staging tells it from a value lost on the way
NOT_AVAILABLE = "n.a"
# what the values of a row are, decided here, judged by staging:
# - measured: ml at UNRELIABLE_READING_MAX_ML or more
# - unreliable: ml below it, whatever the pen gave: the values are kept, n.a when the probe was dry
# - skipped: the room was skipped. date_time is when, every value is n.a
MEASURED = "measured"
UNRELIABLE = "unreliable"
SKIPPED = "skipped"
# below this ml a reading is unreliable, and only then may the probe be dry. the same as unreliable_reading_max_ml
# in DataWarehouseDbt/dbt_project.yml: change both together
UNRELIABLE_READING_MAX_ML = 300
# every reading is taken at this bench for now
BENCH = "4"
# the values of a reading, the ones a dry probe has not got
VALUE_COLUMNS = ("ec", "ph", "temperature")
# the rooms of each part of the day, in the order they are taken
ROOMS = {
    "morning": ("1.30", "1.29", "1.28", "1.27", "1.26", "1.25", "1.24", "0.31", "0.32", "0.33"),
    "afternoon": ("1.23", "1.22", "1.21", "1.20", "1.19", "1.18", "1.17", "0.27", "0.28", "0.29"),
    "mothers": ("0.14", "0.15"),
}
# where the csv goes once every room of the part of the day is done, such as 261020-1.csv
# - a subfolder of the output folder, named only here, and made when it is missing
DEFAULT_DAILY_DIR = Path(os.environ["USER_OUTPUT_MOUNT"]) / "journal_entries"
# read here, not from the container's clock, which falls back to UTC silently: an empty or unknown TZ stops the
# readings before the first one
TIMEZONE = ZoneInfo(os.environ["TZ"])
PART_NUMBERS = {"morning": 1, "afternoon": 2, "mothers": 3}
# the lines of a room, in the order they are taken
LINE_NAMES = ("Drip Left", "Drip Right", "Drain Left", "Drain Right")
# the rooms with other lines than LINE_NAMES: 10 drips and 10 drains, taken drip_1, drain_1, drip_2, ...
ROOM_LINE_NAMES = {
    room_name: tuple(f"{kind}_{number}" for number in range(1, 11) for kind in ("drip", "drain"))
    for room_name in ("0.14", "0.15")
}


def line_names(room_name: str) -> tuple[str, ...]:
    """The lines of the room, in the order they are taken."""
    return ROOM_LINE_NAMES.get(room_name, LINE_NAMES)


def now() -> str:
    """The time of a reading, in TIMEZONE but written without it, as in a journal entries export."""
    return datetime.now(TIMEZONE).replace(tzinfo=None).isoformat(timespec="microseconds")


def csv_values(ec: float | None, ph: float | None, temperature: float | None) -> dict:
    """The values as the csv stores them, NOT_AVAILABLE for none."""
    # a dry probe has no ec, and its ph and temperature are not of the water either
    if ec is None:
        return dict.fromkeys(VALUE_COLUMNS, NOT_AVAILABLE)
    return {
        "ec": f"{ec:.2f}",
        "ph": NOT_AVAILABLE if ph is None else f"{ph:.2f}",
        "temperature": NOT_AVAILABLE if temperature is None else f"{temperature:.1f}",
    }


# a line without a reading yet, for the screen only: never written
NO_VALUES = dict.fromkeys(VALUE_COLUMNS, "")


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
        names = line_names(self.name)
        return names[len(names) - self.lines :]

    def move(self, step: int) -> None:
        """Goes step lines down, up when negative, and to the confirmation only when the room is complete."""
        last = self.lines if self.complete else self.lines - 1
        self.line = max(0, min(last, self.line + step))

    def switch(self, to_ml: bool) -> None:
        """Goes from the readings to the ml or back, on the same line."""
        self.typing_ml = to_ml

    def type_digit(self, digit: str) -> str | None:
        """Adds the digit to the ml of the line. Why its reading was dropped when it was, else None."""
        self.ml[self.line] += digit
        if self._dry_at_too_much_ml(self.line):
            self.readings[self.line] = None
            return f"the probe was dry, which is allowed only below {UNRELIABLE_READING_MAX_ML} ml. take it again"
        return None

    def next_line(self) -> None:
        """Goes on from a line whose ml is typed."""
        if self.ml[self.line]:
            self._advance(self.ml)

    def delete(self) -> None:
        """Removes the ml or the reading of the line. On a line without one, goes back to the one before."""
        if self.confirming:
            self.line -= 1
            return
        if self.typing_ml and self.ml[self.line]:
            self.ml[self.line] = ""
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
        if self._dry_at_too_much_ml(self.line):
            self.readings[self.line] = None
            return f"the probe is dry, which is allowed only below {UNRELIABLE_READING_MAX_ML} ml. take it again"
        self._advance(self.readings)
        return None

    def _dry_at_too_much_ml(self, line: int) -> bool:
        """The line has a dry reading (no ec) at an ml that is not low enough for it: staging would refuse it."""
        reading = self.readings[line]
        return (
            reading is not None
            and reading["ec"] == NOT_AVAILABLE
            and bool(self.ml[line])
            and int(self.ml[line]) >= UNRELIABLE_READING_MAX_ML
        )

    def confirm(self) -> None:
        self.saving = True

    def rows(self, pen_name: str) -> list[dict]:
        """The confirmed room as rows of the csv, one per line."""
        return [
            {
                **self._row(line_name, pen_name),
                "ml": str(int(ml)),
                **reading,
                # a dry probe is refused at more ml (record, type_digit), so it is always unreliable here
                "reading_status": UNRELIABLE if int(ml) < UNRELIABLE_READING_MAX_ML else MEASURED,
            }
            for line_name, ml, reading in zip(self.line_names, self.ml, self.readings)
        ]

    def skipped_rows(self, pen_name: str) -> list[dict]:
        """The skipped room as rows of the csv, one per line still to take, so the file keeps a row for every line,
        and continues past the room. date_time is when it was skipped, every value NOT_AVAILABLE."""
        skipped_at = now()
        return [
            {
                **self._row(line_name, pen_name),
                "date_time": skipped_at,
                "ml": NOT_AVAILABLE,
                **csv_values(None, None, None),
                "reading_status": SKIPPED,
            }
            for line_name in self.line_names
        ]

    def _row(self, line_name: str, pen_name: str) -> dict:
        """What every row of the room has, whether taken or skipped. remarks stays empty for now."""
        if not pen_name:
            raise PenNameMissing("the pen has no name, so no row can be written")
        row = dict.fromkeys(CSV_COLUMNS, "")
        # Drip Left becomes drip_left. the rooms of ROOM_LINE_NAMES have drip_1 and so on, which staging refuses
        row.update(device=pen_name, spot=line_name.lower().replace(" ", "_"), room=self.name, bench=BENCH)
        return row

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


class PenNameMissing(ValueError):
    """The pen connected has no name, which the csv needs as its device."""


class HeaderNotRecognized(ValueError):
    """The header of the csv is not CSV_COLUMNS, such as a csv left by a version that writes other columns."""


def read_csv() -> list[dict]:
    """The rows of the csv, without empty lines. Creates the csv with its header if it is missing or empty."""
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists() or not CSV_PATH.read_text().strip():
        CSV_PATH.write_text(",".join(CSV_COLUMNS) + "\n")
    with CSV_PATH.open(newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise HeaderNotRecognized(
                f"header of {CSV_PATH.name} not recognized: {','.join(reader.fieldnames or ())}, "
                f"expected {','.join(CSV_COLUMNS)}"
            )
        return [row for row in reader if any((cell or "").strip() for cell in row.values())]


def next_room(rows: list[dict], part_of_day: str) -> Room | None:
    """The room of the part of the day that continues from the last row, with the lines it still needs.

    A skipped room has its rows too, so the csv alone tells where to continue. None when every room
    is done. Every row must be of the part of the day: a csv of the other one is not continued.
    """
    rooms = ROOMS[part_of_day]
    others = sorted({row["room"] for row in rows} - set(rooms))
    if others:
        raise ValueError(
            f"{CSV_PATH.name} has rows of rooms {', '.join(others)}, which are not rooms of this part of the day"
        )
    start = 0
    if rows:
        last = rows[-1]["room"]
        index = rooms.index(last)
        # the rows of the last room are the ones at the end with its room
        in_room = 0
        for row in reversed(rows):
            if row["room"] != last:
                break
            in_room += 1
        if in_room < len(line_names(last)):
            return Room(last, len(line_names(last)) - in_room)
        start = index + 1
    following = rooms[start] if start < len(rooms) else None
    return Room(following, len(line_names(following))) if following is not None else None


def append_rows(rows: list[dict]) -> None:
    """Appends the rows to the csv. A PermissionError while the csv is open in another program."""
    # a hand edit can leave empty lines (blank, or only commas when Excel empties a row) at the end,
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


def daily_csv(daily_dir: Path, part_of_day: str) -> Path:
    """Where the csv of the part of the day is saved in the daily folder, such as 261020-1.csv."""
    return daily_dir / f"{datetime.now(TIMEZONE):%y%m%d}-{PART_NUMBERS[part_of_day]}.csv"


def archive_csv(target: Path) -> None:
    """Copies the csv to target, overwriting a file there, and leaves the csv with its header only.
    Makes the folder of target when it is missing, such as after its name changed in DEFAULT_DAILY_DIR."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CSV_PATH, target)
    CSV_PATH.write_text(",".join(CSV_COLUMNS) + "\n")
