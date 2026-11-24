"""The csv of the journal entries confirmed: the only record of them, which the page is drawn from.

Everything of how a journal entry is written is here: the columns, the spot and the values as text,
and what the warehouse needs of a row, such as its reading_status.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
# the decimals of each live value in the csv
DECIMALS = {"ph": 2, "ec": 2, "temperature": 1}
# a value not taken, in the csv. never an empty string, so staging tells it from a value lost on the way
NOT_AVAILABLE = "n.a"
# below this ml a journal entry is unreliable, else measured. the same as unreliable_reading_max_ml in
# DataWarehouseDbt/dbt_project.yml: change both together
UNRELIABLE_READING_MAX_ML = 300
# every journal entry is taken at this bench for now, as in bluelab_datastreamer/drip_drain.py
BENCH = "4"
# read here, not from the container's clock, which falls back to UTC silently: an empty or unknown TZ stops the app
TIMEZONE = ZoneInfo(os.environ["TZ"])


def csv_spot(spot: str) -> str:
    """The spot as the csv writes it: Drip Left becomes drip_left."""
    return spot.lower().replace(" ", "_")


class JournalCsv:
    """The csv at path: one row per journal entry confirmed, at most one per spot.

    Made with its header when missing. One visitor at a time works on it, so nothing guards against
    another writing at once. A few rows on a local disk, so it is read and written in the event loop.
    A PermissionError while the csv is open in another program, such as Excel.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def rows(self) -> dict[str, dict]:
        """The rows, by spot as the csv writes it."""
        self._create()
        with self.path.open(newline="") as file:
            reader = csv.DictReader(file)
            if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
                raise ValueError(f"header of {self.path.name} not recognized: {','.join(reader.fieldnames or ())}")
            return {row["spot"]: row for row in reader}

    def append(self, spot: str, values: dict[str, float | None], ml: int, remarks: str, device: str) -> None:
        """Appends the journal entry of the spot, taken now by the device. room stays empty for now.

        values: each of DECIMALS, None for one not taken. The spot has no row yet: the room appends only
        the one of its current spot.
        """
        row = dict.fromkeys(CSV_COLUMNS, "")
        row.update(
            date_time=datetime.now(TIMEZONE).replace(tzinfo=None).isoformat(timespec="microseconds"),
            device=device,
            spot=csv_spot(spot),
            ml=str(ml),
            bench=BENCH,
            # only spaces is none
            remarks=remarks.strip(),
            reading_status="unreliable" if ml < UNRELIABLE_READING_MAX_ML else "measured",
        )
        for quantity, decimals in DECIMALS.items():
            value = values[quantity]
            row[quantity] = NOT_AVAILABLE if value is None else f"{value:.{decimals}f}"
        self._create()
        with self.path.open("a", newline="") as file:
            csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n").writerow(row)

    def delete(self, spot: str) -> None:
        """Removes the row of the spot, by writing the csv again without it."""
        kept = [row for row in self.rows().values() if row["spot"] != csv_spot(spot)]
        with self.path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(kept)

    def _create(self) -> None:
        if not self.path.exists():
            self.path.write_text(",".join(CSV_COLUMNS) + "\n")
