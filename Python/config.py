from pathlib import Path

# --- Root of the repo = the parent folder of the folder this file lives in ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- File paths ---
JOURNAL_ENTRIES_CSV = BASE_DIR / "SampleData" / "drip_drain_csv" / "journal-entries.csv"
JOURNAL_ENTRIES_MALFORMED_CSV = BASE_DIR / "SampleData" / "drip_drain_csv"/ "malformed_csv" / "journal-entries-text-without-quotes.csv"

# --- Database connection (fill in as you set this up) ---
DB_SERVER = "localhost"
DB_NAME = "DataWarehouse"
DB_SCHEMA_BRONZE = "bronze"
TBL_JOURNAL_ENTRIES = "journal_entries"

ENGINE_STRING =  (f"mssql+pyodbc://{DB_SERVER}/{DB_NAME}"
"?driver=ODBC+Driver+18+for+SQL+Server"
"&trusted_connection=yes"
"&TrustServerCertificate=yes")