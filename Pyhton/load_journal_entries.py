import datetime
import pandas as pd
from pathlib import Path


from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, DataError, IntegrityError

from config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, ENGINE_STRING, JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, TBL_JOURNAL_ENTRIES



 # Test database connection, adds a database connection to the pool.
def connect_to_database(engine, db_server: str, db_name: str):
    print(f"Connecting to database \"{db_name}\" on server \"{db_server}\"...")
    try:
        with engine.connect() as connection:
            print("Connection successfull")
    except OperationalError as e:
        print(f"Could not reach the server (check server name, is SQL Server running, network/firewall): {e}")
        raise #failing to connect to the database is a fatal error, so we re-raise the exception to stop execution
    except Exception as e:
        print(f"Unable to connect to the database, check config.py: {e}")
        raise #failing to connect to the database is a fatal error, so we re-raise the exception to stop execution


def read_csv_file(csv_path: Path) -> pd.DataFrame:
    print(f"Loading CSV file: {csv_path}")

    #check that the file has a .csv extension, case insensitive
    if csv_path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV file, got: {csv_path.suffix}")

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


def validate_csv_schema(df: pd.DataFrame, engine, schema: str, table: str): 
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

def validate_csv_empty(df: pd.DataFrame):
    if len(df) == 0:
        raise pd.errors.EmptyDataError("CSV has columns names, but has no rows") #columns are present, but no rows of data


#validate that the string values in the CSV do not exceed the max length defined in the database schema for each column
#call this after validate_csv_schema() to ensure that the CSV has the correct columns before checking their lengths
def validate_csv_string_size(df: pd.DataFrame, engine, schema: str, table: str):
    schema_df = get_table_schema(engine, schema, table, include_debug_columns=False)

    if not (schema_df["DATA_TYPE"] == "nvarchar").all():  # all columns must be nvarchar
        raise ValueError(f"All columns in the table {schema}.{table} must be of type nvarchar (with the exception of debug columns that start with an underscore)")


    max_sizes_df = schema_df.set_index("COLUMN_NAME")["CHARACTER_MAXIMUM_LENGTH"]
    max_sizes_df = max_sizes_df[max_sizes_df != -1] # nvarchar(MAX) has a max length of -1 in the schema, no need to check length for these columns

    for col in max_sizes_df.index:
        if col not in df.columns:
            raise ValueError(f" Column '{col}' is not in table {schema}.{table} schema. Call validate_csv_schema() first to check for missing/extra columns.")

    #check if any of the columns in the CSV exceed the max length defined in the schema
    for col_name, max_length in max_sizes_df.items():
        csv_max_length = df[col_name].str.len().max()
        if csv_max_length > max_length: 
            raise ValueError(f"Column '{col_name}' in CSV has a value that exceeds max length of {max_length} defined in table {schema}.{table} schema. Max length in CSV is {csv_max_length}.")


#make initial validation checks on the CSV file before loading it into the database
def validate_csv(df: pd.DataFrame, engine, schema: str, table: str) -> bool:
    try :
        validate_csv_empty(df)
        validate_csv_schema(df, engine, schema, table)
        validate_csv_string_size(df, engine, schema, table)
        return True

    except pd.errors.EmptyDataError as e:
        print(f"CSV file is empty: {e}")
        return False
    except ValueError as e:
        print(f"Schema mismatch, CSV columns don't match target table: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during CSV validation: {e}")
        return False

#should be called after the CSV has been validated, just before loading it into the database
def add_debug_columns(df: pd.DataFrame, time: pd.Timestamp, source_file: Path) -> pd.DataFrame:
    # Add the bronze metadata columns
    df["_load_date_time"] = time
    df["_source_file"] = str(source_file)
    return df


def load_to_database(df: pd.DataFrame, engine, schema: str, table: str, csv_path: Path):

    # Add debug columns to the dataframe before loading it into the database
    df = add_debug_columns(df, pd.Timestamp.now(datetime.timezone.utc), csv_path)

    try:
        with engine.begin() as conn:  # starts a transaction; commits on success, rolls back on any exception
            df.to_sql(name=table, schema=schema, con=conn, if_exists="append", index=False)

        print(f"Loaded {len(df)} rows into {schema}.{table}")

    except ProgrammingError as e:
        print(f"Table or schema not found — check that {schema}.{table} exists and is deployed, or change the schema/table name in config.py: {e}")
        raise
    except DataError as e:
        print(f"Data truncation or type error during insert (value too long/wrong type) make sure to call validate_csv before loading: {e}")
        raise
    except OperationalError as e:
        print(f"Connection lost during insert: {e}")
        raise
    except IntegrityError as e:
        print(f"Constraint violation during insert: {e}")
        raise
    except Exception as e:
        print(f"Unexpected database error during insert: {e}")
        raise


def main():
    engine = create_engine(ENGINE_STRING) #doesnt connect to the database yet, just creates a configuration object for the connection
    connect_to_database(engine, DB_SERVER, DB_NAME)

    filepath = JOURNAL_ENTRIES_CSV
    df = read_csv_file(filepath)

    if validate_csv(df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES):
        load_to_database(df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES, filepath)

if __name__ == "__main__":
    main()
   
