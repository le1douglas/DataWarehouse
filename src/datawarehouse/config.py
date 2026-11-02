import os
from pathlib import Path

# every setting comes from docker/compose.yaml, which passes them to the loader container. no defaults: a missing variable
# stops the loader with a KeyError naming it, instead of silently connecting or reading somewhere else
POSTGRES_CONFIG = {
    "db_server": os.environ["POSTGRESQL_SERVER"],
    "db_name": os.environ["POSTGRESQL_DB"],
    "db_user": os.environ["POSTGRESQL_USER"],
    "db_password": os.environ["POSTGRESQL_PASSWORD"],
    "db_port": int(os.environ["POSTGRESQL_PORT"]),
}

# the schema that python loads into, everything else is created by dbt
DB_SCHEMA_BRONZE = "dw_bronze"

# what failed in a dbt run, created by dbt
DB_SCHEMA_AUDIT = "dw_audit"
VW_AUD_FAILURES = "aud_failures"

TBL_BRNZ_JOURNAL_ENTRIES = "brnz_journal_entries"

# the input. compose mounts a windows folder read only at this path in the loader container (EXPORTS_DIR in the
# environment's env file), and JOURNAL_ENTRIES_CSV in the same file names the csv relative to it
INBOX_EXPORTS = Path("/inbox/exports")

JOURNAL_ENTRIES_CSV = INBOX_EXPORTS / os.environ["JOURNAL_ENTRIES_CSV"]


# the dbt project in the image, in dev the one of the mounted repo, at the same path
DBT_PROJECT_DIR = "/usr/app/DataWarehouseDbt"

# what a load of the journal entries builds: silver, all it needs, and what reads it
DBT_SELECT_JOURNAL_ENTRIES = "+slvr_journal_entries+"

# the name of a dataset, as used in table names (brnz_journal_entries)
DATASET_JOURNAL_ENTRIES = "journal_entries"

# row_id identifies a journal entry, it is assigned by the database when the row enters bronze
KEY_JOURNAL_ENTRIES = ["row_id"]

# --- Root of the repo = the parent folder of the folder this file lives in ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- File paths ---
JOURNAL_ENTRIES_MALFORMED_CSV = BASE_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv" / "valid.csv"
