import datetime
from sqlite3 import InterfaceError, OperationalError, ProgrammingError
import pandas as pd
from pathlib import Path

from sqlalchemy import create_engine, text
from config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, ENGINE_STRING, JOURNAL_ENTRIES_CSV, TBL_JOURNAL_ENTRIES


engine = create_engine(ENGINE_STRING) #doesnt connect to the database yet, just creates a configuration object for the connection

 # Test database connection, adds a database connection to the pool.
def connect_to_database(engine, db_server: str, db_name: str):
    print(f"Connecting to database \"{db_name}\" on server \"{db_server}\"...")
    try:
        with engine.connect() as connection:
            print("Connection successful")
    except OperationalError as e:
        print(f"Could not reach the server (check server name, is SQL Server running, network/firewall): {e}")
        raise #failing to connect to the database is a fatal error, so we re-raise the exception to stop execution
    except Exception as e:
        print(f"Unable to connect to the database, check config.py: {e}")
        raise #failing to connect to the database is a fatal error, so we re-raise the exception to stop execution


def read_csv_file(csv_path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path, dtype=str)  # no implicit type conversion on bronze layer, all columns as string
        print(df)
        print(f"Loaded {len(df)} rows")
        return df

    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
        print(f"Error opening CSV file; check that the file exists and is not already opened by another program: {e}")
    except pd.errors.EmptyDataError as e:
        print(f"CSV file is empty: {e}")
    except (pd.errors.ParserError, UnicodeDecodeError) as e:
        print(f"Error parsing CSV file; check that the file is a valid CSV and is encoded as UTF-8: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while reading the CSV file: {e}")


# get the table schema as a dataframe.
# includeDebugColumns decides whether to include columns that start with an underscore: these are used for debugging and are part of the db schema, but are not part of the original source file.
def get_table_schema(engine, schema: str, table: str, includeDebugColumns: bool = False) -> pd.DataFrame:
    query = text("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"schema": schema, "table": table})
        schema_df = pd.DataFrame(result.fetchall(), columns=result.keys())

        if not includeDebugColumns:
            #exclude columns that start with an underscore
            schema_df = schema_df[~schema_df["COLUMN_NAME"].str.startswith("_")]

        return schema_df

def validate_csv_schema(df: pd.DataFrame, engine, schema: str, table: str) -> bool: 
     expected_columns = set(get_table_schema(engine, 
                                         schema, 
                                         table, 
                                         includeDebugColumns=False)["COLUMN_NAME"])
     actual_columns = set(df.columns)

     missing = expected_columns - actual_columns
     extra = actual_columns - expected_columns

     if len(missing) > 0:
        raise ValueError(f"CSV is missing expected columns: {missing}")
     if len(extra) > 0:
        raise ValueError(f"CSV has unexpected extra columns: {extra}")
     
     return True

def validate_csv_empty(df: pd.DataFrame) -> bool:
    if len(df) == 0:
        raise pd.errors.EmptyDataError("CSV has columns names, but has no rows") #columns are present, but no rows of data
    return True

#TODO: implement this function to check that the string lengths in the CSV do not exceed the max lengths defined in the database schema
def validate_csv_string_size(df: pd.DataFrame, engine, schema: str, table: str) -> bool:
    return True 

#make initial validation checks on the CSV file before loading it into the database
def validate_csv(df: pd.DataFrame, engine, schema: str, table: str) -> bool:
    try :
        validate_csv_empty(df)
        validate_csv_schema(df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES)
        validate_csv_string_size(df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES)

    except pd.errors.EmptyDataError as e:
        print(f"CSV file is empty: {e}")
    except ValueError as e:
        print(f"Schema mismatch, CSV columns don't match target table: {e}")

#should be called after the CSV has been validated, just before loading it into the database
def add_debug_columns(df: pd.DataFrame, time: pd.Timestamp, source_file: Path) -> pd.DataFrame:
    # Add the bronze metadata columns
    df["_load_date_time"] = time
    df["_source_file"] = str(source_file)
    return df


#TODO Implement Exception handling
def load_to_database(df: pd.DataFrame, engine, schema: str, table: str):
    
    df.to_sql(
        name= table,
        schema= schema,
        con=engine,
        if_exists="append", 
        index=False # don't write pandas' row index as a column
    )


   
connect_to_database(engine, DB_SERVER, DB_NAME)

df = read_csv_file(JOURNAL_ENTRIES_CSV)

validate_csv(df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES)

df = add_debug_columns(df, pd.Timestamp.now(datetime.timezone.utc), JOURNAL_ENTRIES_CSV)

load_to_database(df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES)