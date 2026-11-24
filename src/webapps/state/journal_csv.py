"""The csv of the journal entries confirmed: the only record of them, which the page is drawn from."""

import csv
from pathlib import Path

# next to this file for now: in dev the repo is mounted, so it outlives the container, but the prod image has its own
CSV_PATH = Path(__file__).parent / "journal_entries.csv"
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


class JournalCsv:
    """The csv at path: one row per journal entry confirmed, at most one per spot.

    Made with its header when missing. One visitor at a time works on it, so nothing guards against
    another writing at once. A few rows on a local disk, so it is read and written in the event loop.
    A PermissionError while the csv is open in another program, such as Excel.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def rows(self) -> dict[str, dict]:
        """The rows, by spot."""
        self._create()
        with self.path.open(newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
                raise ValueError(f"header of {self.path.name} not recognized: {','.join(reader.fieldnames or ())}")
            return {row["spot"]: row for row in reader}

    def text(self) -> str:
        self._create()
        return self.path.read_text()

    def append(self, row: dict) -> None:
        """Appends the row. Its spot has none yet: the page appends only the row of the current spot."""
        with self.path.open("a", newline="") as file:
            csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n").writerow(row)

    def delete(self, spot: str) -> None:
        """Removes the row of the spot, by writing the csv again without it."""
        kept = [row for row in self.rows().values() if row["spot"] != spot]
        with self.path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(kept)

    def _create(self) -> None:
        if not self.path.exists():
            self.path.write_text(",".join(CSV_COLUMNS) + "\n")
