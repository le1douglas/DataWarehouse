import os
from pathlib import Path

# every setting comes from .env.loader, which compose passes to the loader container. no defaults: a missing variable
# stops the loader with a KeyError naming it, instead of silently connecting or reading somewhere else
POSTGRES_CONFIG = {
    "db_server": os.environ["POSTGRESQL_SERVER"],
    "db_name": os.environ["POSTGRESQL_DB"],
    "db_user": os.environ["POSTGRESQL_USER"],
    "db_password": os.environ["POSTGRESQL_PASSWORD"],
    "db_port": int(os.environ["POSTGRESQL_PORT"]),
}

# the schemas that python loads into, everything else is created by dbt
DB_SCHEMA_BRONZE = "dw_bronze"
DB_SCHEMA_CORRECTIONS = "dw_corrections"

TBL_BRNZ_JOURNAL_ENTRIES = "brnz_journal_entries"
TBL_CORR_JOURNAL_ENTRIES = "corr_journal_entries"

# the meta table of a layer holds the metadata of every dataset of that layer
TBL_META_BRONZE = "meta_bronze"
TBL_META_CORRECTIONS = "meta_corrections"

# the sheet of the corrections workbook that is uploaded: the corrections, then their metadata in the last two columns
CORRECTIONS_SHEET = "corrected"

# the inputs. compose mounts two windows folders read only at these paths in the loader container (EXPORTS_DIR and
# CORRECTIONS_DIR in the environment's env file), and .env.loader names each file relative to its folder
INBOX_EXPORTS = Path("/inbox/exports")
INBOX_CORRECTIONS = Path("/inbox/corrections")

JOURNAL_ENTRIES_CSV = INBOX_EXPORTS / os.environ["JOURNAL_ENTRIES_CSV"]
CORRECTIONS_WORKBOOK = INBOX_CORRECTIONS / os.environ["CORRECTIONS_WORKBOOK"]


# the name of a dataset, as used in table names (brnz_journal_entries)
DATASET_JOURNAL_ENTRIES = "journal_entries"

# row_id identifies a journal entry, it is assigned by the database when the row enters bronze
KEY_JOURNAL_ENTRIES = ["row_id"]

# --- Root of the repo = the parent folder of the folder this file lives in ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- File paths ---
JOURNAL_ENTRIES_MALFORMED_CSV = BASE_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv" / "valid.csv"
