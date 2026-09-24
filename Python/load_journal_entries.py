import datetime
import pandas as pd
import csv
from pathlib import Path


from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, DataError, IntegrityError


from config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, ENGINE_STRING, JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, TBL_JOURNAL_ENTRIES



 # Test database connection, adds a database connection to the pool.
def connect_to_db(engine, db_server: str, db_name: str):
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

def validate_db_table_is_nvarchar(db_table_schema_df: pd.DataFrame):
    if not (db_table_schema_df["DATA_TYPE"] == "nvarchar").all():  # all columns must be nvarchar
            raise ValueError(f"All columns in the database table must be of type nvarchar (with the exception of debug columns that start with an underscore)")
    
#check if the number of fields in every row matches the column counts
#TODO find a way to do it in panda
def validate_fields_number_equals_columns_number(csv_path: Path):
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row and len(row) != len(header):  # 'row' is [] for a blank line, pandas skips those too
                    raise pd.errors.ParserError("CSV has a row whose number of fields differs from the header")



def read_csv_file(csv_path: Path) -> pd.DataFrame:
    #print(f"Loading CSV file: {csv_path}")

    #check that the file has a .csv extension, case insensitive
    if csv_path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV file, got: {csv_path.suffix}")

    try:
        df = pd.read_csv(csv_path, 
                         dtype=str, 
                         delimiter=',', 
                         quotechar="\"", #text delimiter
                         on_bad_lines='error',
                         keep_default_na=False,#TODO study this #Pandas treats strings like NA, null and N/A as missing by default 
                         na_values=[""],#TODO study this
                         index_col=False)  # no implicit type conversion on bronze layer, all columns as string
        
        validate_fields_number_equals_columns_number(csv_path)
        
        print(f"Loaded {len(df)} rows")
        return df

    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
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
            # Cast explicitly: pandas infers the type of CHARACTER_MAXIMUM_LENGTH from the data, so it
            # changes depending on which table is queried:
            #   - only integers (all nvarchar columns)  -> int64
            #   - integers mixed with NULLs             -> float64 (-1 becomes -1.0)
            #   - only NULLs (no character columns)     -> object
            # Downstream code compares this column to numbers, so the type has to be the same every time.
            # "Int64" (capital I) is pandas' nullable integer type: it keeps the values as real integers
            # and stores SQL NULL (non-character columns such as datetime2) as pd.NA, which plain int64 can't.
            schema_df = schema_df.astype({"CHARACTER_MAXIMUM_LENGTH": "Int64"})

            if not include_debug_columns:
                #exclude columns that start with an underscore
                schema_df = schema_df[~schema_df["COLUMN_NAME"].str.startswith("_")]

           
            return schema_df
    except Exception as e:
        print(f"An error occurred while retrieving the table schema: {e}")
        raise


def validate_csv_schema(df: pd.DataFrame, db_table_schema_df: pd.DataFrame):

    #check the columns
    expected_columns = set( db_table_schema_df["COLUMN_NAME"])
    actual_columns = set(df.columns)

    missing = expected_columns - actual_columns
    extra = actual_columns - expected_columns

    if len(missing) > 0:
        raise ValueError(f"CSV is missing expected columns: {missing}")
    if len(extra) > 0:
        raise ValueError(f"CSV has unexpected extra columns: {extra}")

    #check if any of the columns in the CSV contrains a string that exceeds the max length defined in the schema
    max_sizes_df = db_table_schema_df.set_index("COLUMN_NAME")["CHARACTER_MAXIMUM_LENGTH"]
    max_sizes_df = max_sizes_df[max_sizes_df != -1] # nvarchar(MAX) has a max length of -1 in the schema, no need to check length for these columns

    for col_name, max_length in max_sizes_df.items():
        csv_max_length = df[col_name].str.len().max()
        if csv_max_length > max_length: 
           raise ValueError(f"Column '{col_name}' in CSV has a value that exceeds max length of {max_length} defined in target table schema. Max length in CSV is {csv_max_length}.")           


def validate_csv_empty(df: pd.DataFrame):
    if len(df) == 0:
        raise pd.errors.EmptyDataError("CSV has columns names, but has no rows") #columns are present, but no rows of data


#make initial validation checks on the CSV file before loading it into the database
def validate_csv(csv_df: pd.DataFrame,  db_table_schema_df: pd.DataFrame) -> bool:
    try :
        validate_csv_empty(csv_df)
        validate_csv_schema(csv_df, db_table_schema_df)
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
    connect_to_db(engine, DB_SERVER, DB_NAME)
    
    #the schema of the target table, as a dataframe
    db_table_schema_df = get_table_schema(engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES, include_debug_columns=False)
    validate_db_table_is_nvarchar(db_table_schema_df)
    
    
    filepath = JOURNAL_ENTRIES_CSV
    csv_df = read_csv_file(filepath)

    if validate_csv(csv_df, db_table_schema_df):
        load_to_database(csv_df, engine, DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES, filepath)
        return

if __name__ == "__main__":
    main()
   
