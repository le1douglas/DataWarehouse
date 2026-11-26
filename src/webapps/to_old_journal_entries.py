"""Temporary: the csv of a walk in the old journal entries format, the Bluelab export the datastreamer wrote before
the new csv schema. Written by the review page's Export, next to the new csv, until nothing reads the old format.

The old format has no spot, bench or reading_status:
- a spot is told only by its place in its room, so the rows are in the walk's order, as the datastreamer wrote them
- a skipped entry has no row, as a skipped room had none
"""

import csv
from pathlib import Path

from webapps.settings import WalkSettings
from webapps.state.journal_entry import SKIPPED
from webapps.state.journal_entry_csv import NOT_AVAILABLE

OLD_CSV_COLUMNS = (
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


def write_old_journal_entries(rows: list[dict[str, str]], walk: WalkSettings, target: Path) -> None:
    """Writes the rows of the new csv to target in the old format, overwriting a file there. Makes the folder of
    target when missing."""
    kept = [row for row in rows if row["reading_status"] != SKIPPED]
    kept.sort(key=lambda row: _walk_position(row, walk))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OLD_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(_to_old_row(row) for row in kept)


def _walk_position(row: dict[str, str], walk: WalkSettings) -> tuple[int, int, int]:
    """Where the row is taken in the walk: its room, then its bench, then its spot."""
    return walk.rooms.index(row["room"]), walk.benches.index(row["bench"]), walk.spots.index(row["spot"])


def _to_old_row(row: dict[str, str]) -> dict[str, str]:
    """The old row of a new one.

    - notes: the ml, then the remarks
    - n.a is empty, as the old format has none
    - tags: the room
    """
    notes = " ".join(value for value in (_old_value(row["ml"]), row["remarks"]) if value)
    old_row = dict.fromkeys(OLD_CSV_COLUMNS, "")
    old_row.update(
        date_time=row["date_time"],
        subject=f"{row['device']} - Measurement",
        notes=notes,
        type="measurement",
        ec=_old_value(row["ec"]),
        ph=_old_value(row["ph"]),
        temp=_old_value(row["temperature"]),
        tags=row["room"],
    )
    return old_row


def _old_value(value: str) -> str:
    return "" if value == NOT_AVAILABLE else value
