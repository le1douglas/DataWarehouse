"""What differs per site and setup, not with the code: changed here, without touching any logic."""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

# the rooms the app steps through, in the order they are walked: the app's own list
ROOMS = (
    "1.30",
    "1.29",
    "1.28",
    "1.27",
    "1.26",
    "1.25",
    "1.24",
    "0.31",
    "0.32",
    "0.33",
    "1.23",
    "1.22",
    "1.21",
    "1.20",
    "1.19",
    "1.18",
    "1.17",
    "0.27",
    "0.28",
    "0.29",
)
# every journal entry is taken at this bench for now, as in bluelab_datastreamer/drip_drain.py
BENCH = "4"
# read here, not from the container's clock, which falls back to UTC silently: an empty or unknown TZ stops the app
TIMEZONE = ZoneInfo(os.environ["TZ"])
# the csv of the journal entries confirmed, in state/ for now
# - in dev the repo is mounted, so it outlives the container, but the prod image has its own
CSV_PATH = Path(__file__).parent / "state" / "journal_entries.csv"
