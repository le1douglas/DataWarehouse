import os
from pathlib import Path
from zoneinfo import ZoneInfo

# every setting comes from .env.loader, which compose passes to the loader container. no defaults: a missing variable
# stops the loader with a KeyError naming it, instead of silently connecting or reading somewhere else
POSTGRES_CONFIG = {
    "db_server": os.environ["POSTGRESQL_SERVER"],
    "db_name": os.environ["POSTGRESQL_DB"],
    "db_user": os.environ["POSTGRESQL_USER"],
    "db_password": os.environ["POSTGRESQL_PASSWORD"],
    "db_port": int(os.environ["POSTGRESQL_PORT"]),
}

# the time zone of the date-times the loader stamps, from TZ, set once in docker/compose.yaml. read here instead of
# taken from the container's clock, which falls back to UTC without an error: an empty or unknown TZ stops the loader
TIMEZONE = ZoneInfo(os.environ["TZ"])

# the schema that python loads into, everything else is created by dbt or written by the web apps
DB_SCHEMA_BRONZE = "dw_bronze"

TBL_BRNZ_JOURNAL_ENTRIES = "brnz_journal_entries"

# the meta table of a layer holds the metadata of every dataset of that layer
TBL_META_BRONZE = "meta_bronze"

# the input. compose mounts a windows folder read only at this path in the loader container (EXPORTS_DIR in the
# environment's env file), and .env.loader names each file relative to it
INBOX_EXPORTS = Path("/inbox/exports")

JOURNAL_ENTRIES_CSV = INBOX_EXPORTS / os.environ["JOURNAL_ENTRIES_CSV"]


# the name of a dataset, as used in table names (brnz_journal_entries)
DATASET_JOURNAL_ENTRIES = "journal_entries"

# row_id identifies a journal entry, it is assigned by the database when the row enters bronze
KEY_JOURNAL_ENTRIES = ["row_id"]

# --- Root of the repo = the parent folder of the folder this file lives in ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- File paths ---
JOURNAL_ENTRIES_MALFORMED_CSV = BASE_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv" / "valid.csv"
