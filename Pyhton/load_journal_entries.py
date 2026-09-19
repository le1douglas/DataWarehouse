import datetime

import pandas as pd
from sqlalchemy import create_engine, text
from config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, ENGINE_STRING, JOURNAL_ENTRIES_CSV, TBL_JOURNAL_ENTRIES


engine = create_engine(ENGINE_STRING)

# Connect to the database
print(f"Connecting to database \"{DB_NAME}\" on server \"{DB_SERVER}\"...")
try:
    with engine.connect() as connection:
        print("Connection successful")
except Exception as e:
    print(f"Connection failed: {e}")


# read CSV file
df = pd.read_csv(JOURNAL_ENTRIES_CSV, dtype=str)  # no implicit type conversion on bronze layer, all columns as string
print(df.head())
print("...")
print(f"Loaded {len(df)} rows")

# Add the bronze metadata columns
df["_load_date_time"] = pd.Timestamp.now(datetime.timezone.utc)
df["_source_file"] = str(JOURNAL_ENTRIES_CSV)


df.to_sql(
    name= TBL_JOURNAL_ENTRIES,
    schema= DB_SCHEMA_BRONZE,
    con=engine,
    if_exists="append", 
    index=False # don't write pandas' row index as a column
)


