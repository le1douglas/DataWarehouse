"""What differs per site and setup, not with the code: changed here, without touching any logic."""

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class WalkSettings:
    """What a walk measures: its rooms in the order they are walked, and in every room the same benches and spots.

    In a room, every spot of a bench, then the next bench: the journal entries in the order they are taken.
    """

    rooms: tuple[str, ...]
    benches: tuple[str, ...]
    # as the csv writes them
    spots: tuple[str, ...]
    # the number of its export in EXPORT_DIR, <yymmdd>-<number>.csv: as PART_NUMBERS of the datastreamer
    export_number: int


# the walks, by the name in their url: the app's own lists
# - the rooms of each are those of its room_time in seed_rooms.csv
WALKS = {
    "morning": WalkSettings(
        rooms=("1.30", "1.29", "1.28", "1.27", "1.26", "1.25", "1.24", "0.31", "0.32", "0.33"),
        benches=("4",),
        spots=("drip_left", "drip_right", "drain_left", "drain_right"),
        export_number=1,
    ),
    "afternoon": WalkSettings(
        rooms=("1.23", "1.22", "1.21", "1.20", "1.19", "1.18", "1.17", "0.27", "0.28", "0.29"),
        benches=("4",),
        spots=("drip_left", "drip_right", "drain_left", "drain_right"),
        export_number=2,
    ),
    "mother": WalkSettings(
        rooms=("0.14", "0.15"),
        benches=("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"),
        spots=("drip_left", "drain_left"),
        export_number=3,
    ),
}
# read here, not from the container's clock, which falls back to UTC silently: an empty or unknown TZ stops the app
TIMEZONE = ZoneInfo(os.environ["TZ"])
# the folder of the csvs of the journal entries confirmed, one per walk: journal_entries_<walk>.csv. made when missing
# - in dev the repo is mounted, so they outlive the container, but the prod image has its own
CSV_DIR = Path(__file__).parent / "outputs"
# the folder the review page exports the csv of a walk to: the user's output folder (USER_OUTPUT_DIR in the env
# file), the subfolder the datastreamer writes its csvs to. made when missing
EXPORT_DIR = Path(os.environ["USER_OUTPUT_MOUNT"]) / "journal_entries"
