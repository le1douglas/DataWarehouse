import pandas as pd
import datetime
import pandas as pd
from pathlib import Path


from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, DataError, IntegrityError

from database_table import DatabaseTable


class SQLServerDatabase:

    def __init__(self, db_server: str, db_name: str):
        connection_string =  (f"mssql+pyodbc://{db_server}/{db_name}"
                                "?driver=ODBC+Driver+18+for+SQL+Server"
                                "&trusted_connection=yes"
                                "&TrustServerCertificate=yes")
        self.db_server = db_server
        self.db_name = db_name
        self.engine: Engine = create_engine(connection_string)

        self.tablesList = self._getTablesList()

    # Adds a database connection to the pool.
    def connect(self):
        print(f"Connecting to database \"{self.db_name}\" on server \"{self.db_server}\"...")
        try:
            with self.engine.connect() as connection:
                print("Connection successfull")
        except OperationalError as e:
            print(f"Could not reach the server (check that server \"{self.db_server}\" exists, that is running, and there are no network/firewall issues): {e}")
            raise
        except Exception as e:
            print(f"Uknown exception occured while connecting to \"{self.db_server}\": {e}")
            raise


    def _getTablesList(self) -> list[DatabaseTable]:
        query = text("""
                    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                    FROM INFORMATION_SCHEMA.COLUMNS
                """)
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                combined_schema_df = pd.DataFrame(result.fetchall(), columns=result.keys())
                # Cast explicitly: pandas infers the type of CHARACTER_MAXIMUM_LENGTH from the data, so it
                # changes depending on which table is queried:
                #   - only integers (all nvarchar columns)  -> int64
                #   - integers mixed with NULLs             -> float64 (-1 becomes -1.0)
                #   - only NULLs (no character columns)     -> object
                # Downstream code compares this column to numbers, so the type has to be the same every time.
                # "Int64" (capital I) is pandas' nullable integer type: it keeps the values as real integers
                # and stores SQL NULL (non-character columns such as datetime2) as pd.NA, which plain int64 can't.
                combined_schema_df = combined_schema_df.astype({"CHARACTER_MAXIMUM_LENGTH": "Int64"})


                grouped = combined_schema_df.groupby(["TABLE_SCHEMA", "TABLE_NAME"])

                tables = []
                for (layer_val, name_val), group in grouped:

                    schema = group[["COLUMN_NAME", "DATA_TYPE", "CHARACTER_MAXIMUM_LENGTH"]]
                    schema = schema.reset_index(drop=True)

                    table = DatabaseTable(layer=layer_val, name=name_val, schema=schema)
                    tables.append(table)



                return tables
        except Exception as e:
            print(f"An error occurred while retrieving the table schema:\n\r {e}")
            raise
    


    #should be called after the CSV has been validated, just before loading it into the database
    def _add_debug_columns(self, df: pd.DataFrame, time: pd.Timestamp, source_file: Path) -> pd.DataFrame:
        # Add the bronze metadata columns
        df["_load_date_time"] = time
        df["_source_file"] = str(source_file)
        return df


    def load_to_bronze(self, table: DatabaseTable, df: pd.DataFrame, original_file_path: Path):

        if not table.isBronze():
            raise ValueError("table must be bronze layer")
        

        # Add debug columns to the dataframe before loading it into the database
        df = self._add_debug_columns(df, pd.Timestamp.now(datetime.timezone.utc), original_file_path)

        try:
            with self.engine.begin() as conn:  # starts a transaction; commits on success, rolls back on any exception
                df.to_sql(name=table.getName(), schema = table.getLayer(), con=conn, if_exists="append", index=False)

            print(f"Loaded {len(df)} rows into {table.getLayer()}.{table.getName()}")

        except ProgrammingError as e:
            print(f"Table or schema not found — check that {table.getLayer()}.{table.getName()} exists and is deployed, or change the schema/table name in config.py: {e}")
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

    def getTable(self, layer: str, table_name: str)-> DatabaseTable:
        for t in self.tablesList:  
            if t.layer.lower() == layer.lower() and t.name.lower() == table_name.lower():
             return t
        raise KeyError(f"No table found for layer={layer}, name={table_name}")


    # get the table schema as a dataframe.
    # include_debug_columns decides whether to include columns that start with an underscore: these are used for debugging and are part of the db schema, but are not part of the original source file.
    def _get_table_schema(self, schema: str, table_name: str, include_debug_columns: bool) -> pd.DataFrame:
        query = text("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
        """)
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"schema": schema, "table": table_name})
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
