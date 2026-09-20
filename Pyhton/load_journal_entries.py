import datetime
import pandas as pd
from pathlib import Path


from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, ENGINE_STRING, JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, TBL_JOURNAL_ENTRIES


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
        #TODO when provided with CSV with more values than columns, it will truncate the extra values silently. Need to find a way to throw an exception.
        df = pd.read_csv(csv_path, dtype=str, delimiter=',', on_bad_lines='error', index_col=False)  # no implicit type conversion on bronze layer, all columns as string
        print(df)
        print(f"Loaded {len(df)} rows")
        return df

    except (FileNotFoundError, PermissionError, IsADirectoryError) as e: #unable to trigger IsADirectoryError, pointing to directory triggers a PermissionError
        print(f"Error opening CSV file; check that the file exists and is not already opened by another program: {e}")
        raise
    except pd.errors.EmptyDataError as e:
        print(f"CSV file is empty: {e}")
        raise
    except (pd.errors.ParserError, UnicodeDecodeError) as e:
        print(f"Error parsing CSV file; check that the file is a valid CSV and is encoded as UTF-8: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while reading the CSV file: {e}")
        raise


# get the table schema as a dataframe.
# include_debug_columns decides whether to include columns that start with an underscore: these are used for debugging and are part of the db schema, but are not part of the original source file.
def get_table_schema(engine, schema: str, table: str, include_debug_columns: bool = False) -> pd.DataFrame:
    query = text("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
    """)
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"schema": schema, "table": table})
            schema_df = pd.DataFrame(result.fetchall(), columns=result.keys())

            if not include_debug_columns:
                #exclude columns that start with an underscore
                schema_df = schema_df[~schema_df["COLUMN_NAME"].str.startswith("_")]

            return schema_df
    except Exception as e:
        print(f"An error occurred while retrieving the table schema: {e}")
        raise


def validate_csv_schema(df: pd.DataFrame, engine, schema: str, table: str) -> bool: 
     expected_columns = set(get_table_schema(engine, 
                                         schema, 
                                         table, 
                                         include_debug_columns=False)["COLUMN_NAME"])
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
# be careful of nvarchar(MAX)
def validate_csv_string_size(df: pd.DataFrame, engine, schema: str, table: str) -> bool:
    return True 

#make initial validation checks on the CSV file before loading it into the database
def validate_csv(df: pd.DataFrame, engine, schema: str, table: str) -> bool:
    try :
        validate_csv_empty(df)
        validate_csv_schema(df, engine, schema, table)
        validate_csv_string_size(df, engine, schema, table)
        return True

    except pd.errors.EmptyDataError as e:
        print(f"CSV file is empty: {e}")
        raise
    except ValueError as e:
        print(f"Schema mismatch, CSV columns don't match target table: {e}")
        raise

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


def main():

    filepath = JOURNAL_ENTRIES_MALFORMED_CSV
    print(f"Loading CSV file: {filepath}")

    connect_to_database(engine, DB_SERVER, DB_NAME)

    df = read_csv_file(filepath)

    if validate_csv(df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES):
        df = add_debug_columns(df, pd.Timestamp.now(datetime.timezone.utc), filepath)
        load_to_database(df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES)

if __name__ == "__main__":
    main()
   
