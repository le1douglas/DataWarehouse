import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


POSTGRES_CONFIG = {
    "db_server": os.getenv("POSTGRESQL_SERVER", "localhost"),
    "db_name": os.getenv("POSTGRESQL_DB", "DataWarehouse"),
    "db_user": os.getenv("POSTGRESQL_USER", "postgres"),
    "db_password": os.getenv("POSTGRESQL_PASSWORD"),
    "db_port": int(os.getenv("POSTGRESQL_PORT", "5432")),
}

# the schemas that python loads into, everything else is created by dbt
DB_DEV_SCHEMA_BRONZE = "dev_bronze"
DB_DEV_SCHEMA_CORRECTIONS = "dev_corrections"

TBL_BRNZ_JOURNAL_ENTRIES = "brnz_journal_entries"
TBL_CORR_JOURNAL_ENTRIES = "corr_journal_entries"

# the meta table of a layer holds the metadata of every dataset of that layer
TBL_META_BRONZE = "meta_bronze"
TBL_META_CORRECTIONS = "meta_corrections"

# the two sheets of the corrections workbook that are uploaded: the corrections and their metadata.
# the metadata sheet has the columns of the meta table, one row per row_id and kind
SHEET_CORRECTIONS = "corrected"
SHEET_META_CORRECTIONS = "meta_corrections"

# the name of a dataset, as written in the dataset column of the meta tables
DATASET_JOURNAL_ENTRIES = "journal_entries"

# row_id identifies a journal entry, it is assigned by the database when the row enters bronze
KEY_JOURNAL_ENTRIES = ["row_id"]

# --- Root of the repo = the parent folder of the folder this file lives in ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- File paths ---
JOURNAL_ENTRIES_CSV = BASE_DIR / "SampleData" / "drip_drain_csv" / "journal-entries.csv"
JOURNAL_ENTRIES_MALFORMED_CSV = BASE_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv" / "valid.csv"
