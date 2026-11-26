"""The csv of the journal entries confirmed, of every room: the only record of them, which the page is drawn from.

Everything of the file's format is here: the columns, n.a, the decimals, the date_time without its zone.
What a journal entry holds is journal_entry.py: the csv writes it as it is.
"""

import csv
from datetime import datetime
from pathlib import Path

from webapps.settings import TIMEZONE
from webapps.state.journal_entry import METRICS, JournalEntry
from webapps.state.room import BenchSpot

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
# the decimals of each live value
DECIMALS = {"ph": 2, "ec": 2, "temperature": 1}
# a value not taken: None in a journal entry. never an empty string, so staging tells it from a value lost on the way
NOT_AVAILABLE = "n.a"


class JournalEntryCsv:
    """The csv at path: one row per journal entry confirmed, at most one per room and spot.

    It holds one walk, one csv for each: emptied by hand before its next pass. Made with its header when missing. Only
    this app works on it, one visitor at a time, so nothing guards against another program or writer.
    A few rows on a local disk, so it is read and written in the event loop.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_entries(self, room: str) -> dict[BenchSpot, JournalEntry]:
        """The journal entries of the room, by bench and spot."""
        return {(row["bench"], row["spot"]): _parse_row(row) for row in self._read_rows() if row["room"] == room}

    def append(self, entry: JournalEntry) -> None:
        """Appends the row of the entry, confirmed. Its room, bench and spot have no row yet: the walk appends
        only the current entry of the open room."""
        self._create()
        with self.path.open("a", newline="") as file:
            csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n").writerow(_format_row(entry))

    def delete(self, room: str, bench_spot: BenchSpot) -> None:
        """Removes the row of the room, bench and spot, by writing the csv again without it. The other rows as
        they were."""
        kept = [row for row in self._read_rows() if (row["room"], row["bench"], row["spot"]) != (room, *bench_spot)]
        with self.path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(kept)

    def read_text(self) -> str:
        """The csv as it is on disk, made with its header when missing."""
        self._create()
        return self.path.read_text()

    def _read_rows(self) -> list[dict[str, str]]:
        self._create()
        with self.path.open(newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
                raise ValueError(f"header of {self.path.name} not recognized: {','.join(reader.fieldnames or ())}")
            return list(reader)

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
