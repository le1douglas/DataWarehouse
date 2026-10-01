from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

MICROSOFT_SQL_CONFIG = {
    "db_server":   os.getenv("MICROSOFT_SQL_SERVER", "localhost"),
    "db_name":     os.getenv("MICROSOFT_SQL_DB", "DataWarehouse")
}


POSTGRES_CONFIG = {
    "db_server":   os.getenv("POSTGRESQL_SERVER", "localhost"),
    "db_name":     os.getenv("POSTGRESQL_DB", "DataWarehouse"),
    "db_user":     os.getenv("POSTGRESQL_USER", "postgres"),
    "db_password": os.getenv("POSTGRESQL_PASSWORD"),
    "db_port":     int(os.getenv("POSTGRESQL_PORT", "5432"))
}


DB_SCHEMA_BRONZE = "prod_bronze"
DB_SCHEMA_SILVER = "prod_silver"
DB_SCHEMA_GOLD = "prod_gold"

TBL_JOURNAL_ENTRIES = "journal_entries"

# --- Root of the repo = the parent folder of the folder this file lives in ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- File paths ---
JOURNAL_ENTRIES_CSV = BASE_DIR / "SampleData" / "drip_drain_csv" / "journal-entries.csv"
JOURNAL_ENTRIES_MALFORMED_CSV = BASE_DIR / "SampleData" / "drip_drain_csv"/ "malformed_csv" / "valid.csv"
