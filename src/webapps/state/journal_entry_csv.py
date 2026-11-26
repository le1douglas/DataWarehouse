"""The csv of the journal entries confirmed, of every room: written from the walk's list, which reads it when the
page opens.

Everything of the file's format is here: the columns, n.a, the decimals, the date_time without its zone.
What a journal entry holds is journal_entry.py: the csv writes it as it is.
"""

import csv
import shutil
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from webapps.settings import TIMEZONE
from webapps.state.journal_entry import METRICS, AbsolutePosition, JournalEntry

# the columns of dw_bronze.brnz_journal_entries, as CSV_COLUMNS in bluelab_datastreamer/drip_drain.py
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
# the columns a review may set, by name: every other stays as the app wrote it
EDITABLE_COLUMNS = ("ml", "ec", "ph", "temperature", "remarks")
# the decimals of each live value
DECIMALS = {"ph": 2, "ec": 2, "temperature": 1}
# a value not taken: None in a journal entry. never an empty string, so staging tells it from a value lost on the way
NOT_AVAILABLE = "n.a"


class JournalEntryCsv:
    """The csv at path: one row per journal entry confirmed, at most one per absolute position.

    It holds one walk, one csv for each: emptied once the review page has exported it. Made with its header when
    missing. Only this app works on it, one visitor at a time, so nothing guards against another program or writer.
    A few rows on a local disk, so it is read and written in the event loop.
    - the walk page writes it whole, from its list. the review page sets values in place
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_entries(self) -> dict[AbsolutePosition, JournalEntry]:
        """Every journal entry of the csv, confirmed, by absolute position.

        - assumed, not checked: each absolute position is of the walk, and once only
        """
        entries = (_parse_row(row) for row in self._read_rows())
        return {entry.get_absolute_position(): entry for entry in entries}

    def write_entries(self, entries: Iterable[JournalEntry]) -> None:
        """Writes the csv again from the confirmed entries, in the order given: the walk's. The others left out."""
        self._write_rows([_format_row(entry) for entry in entries if entry.is_confirmed()])

    def read_rows(self) -> list[dict[str, str]]:
        """Every row as it is on disk, every value as text."""
        return self._read_rows()

    def update_value(self, position: AbsolutePosition, column: str, value: str) -> None:
        """Sets the value of the column in the row of the absolute position, as it is given, by writing the csv
        again. The other values as they were.

        - only the EDITABLE_COLUMNS. room, bench and spot are the key that finds the row
        """
        if column not in EDITABLE_COLUMNS:
            raise ValueError(f"{column} is not a column to set")
        rows = self._read_rows()
        for row in rows:
            if (row["room"], row["bench"], row["spot"]) == position:
                row[column] = value
                self._write_rows(rows)
                return
        room, bench, spot = position
        raise ValueError(f"no row for room {room}, bench {bench}, spot {spot}")

    def read_text(self) -> str:
        """The csv as it is on disk, made with its header when missing."""
        self._create()
        return self.path.read_text()

    def export(self, target: Path) -> None:
        """Copies the csv to target as it is, overwriting a file there. Makes the folder of target when missing."""
        self._create()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.path, target)

    def empty(self) -> None:
        """Removes every row: the header alone, for the walk's next pass."""
        self._write_rows([])

    def _read_rows(self) -> list[dict[str, str]]:
        self._create()
        with self.path.open(newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
                raise ValueError(f"header of {self.path.name} not recognized: {','.join(reader.fieldnames or ())}")
            return list(reader)

    def _write_rows(self, rows: list[dict[str, str]]) -> None:
        with self.path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def _create(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(",".join(CSV_COLUMNS) + "\n")


def format_live_value(metric: str, value: float | None) -> str:
    """A live value as the csv writes it: n.a for one not got."""
    return NOT_AVAILABLE if value is None else f"{value:.{DECIMALS[metric]}f}"


def _format_row(entry: JournalEntry) -> dict[str, str]:
    """The row of a confirmed entry, every value as text: None is n.a."""
    row = {
        # without its zone: staging appends the timezone var
        "date_time": entry.date_time.replace(tzinfo=None).isoformat(timespec="microseconds"),
        "device": entry.device,
        "spot": entry.spot,
        "ml": NOT_AVAILABLE if entry.ml is None else str(entry.ml),
        "room": entry.room,
        "bench": entry.bench,
        # only spaces is none
        "remarks": entry.remarks.strip(),
        "reading_status": entry.reading_status,
    }
    for metric in METRICS:
        row[metric] = format_live_value(metric, getattr(entry, metric))
    return {column: row[column] for column in CSV_COLUMNS}


def _parse_row(row: dict[str, str]) -> JournalEntry:
    """The journal entry of a row: n.a becomes None."""
    live = {metric: _parse_number(row[metric], float) for metric in METRICS}
    return JournalEntry(
        spot=row["spot"],
        room=row["room"],
        bench=row["bench"],
        date_time=datetime.fromisoformat(row["date_time"]).replace(tzinfo=TIMEZONE),
        device=row["device"],
        ml=_parse_number(row["ml"], int),
        remarks=row["remarks"],
        reading_status=row["reading_status"],
        **live,
    )


def _parse_number(text: str, kind: type) -> float | int | None:
    return None if text == NOT_AVAILABLE else kind(text)
