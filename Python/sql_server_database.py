import pandas as pd
import pandas as pd
from pathlib import Path


from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, DataError, IntegrityError

from Python.bronze_record_set import BronzeRecordSet
from database_table import DatabaseTable


class SQLServerDatabase:

    def __init__(self, db_server: str, db_name: str):
     
        self.server = db_server
        self.name = db_name
        connection_string =  (f"mssql+pyodbc://{self.server}/{self.name}"
                                "?driver=ODBC+Driver+18+for+SQL+Server"
                                "&trusted_connection=yes"
                                "&TrustServerCertificate=yes")
        self.engine: Engine = create_engine(connection_string)

        self.tablesList = self._getTablesList()

    # Adds a database connection to the pool.
    def connect(self):
        print(f"Connecting to database \"{self.name}\" on server \"{self.server}\"...")
        try:
            with self.engine.connect() as connection:
                print("Connection successfull")
        except OperationalError as e:
            print(f"Could not reach the server (check that server \"{self.server}\" exists, that is running, and there are no network/firewall issues):\n\r {e}")
            raise
        except Exception as e:
            print(f"Uknown exception occured while connecting to \"{self.server}\":\n\r {e}")
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
    

    def load_to_bronze(self, table: DatabaseTable, record_set: BronzeRecordSet):

        if not table.isBronze():
            raise ValueError(f"Table \"{table.name}\" must be bronze layer")

        try:
            with self.engine.begin() as conn:  # starts a transaction; commits on success, rolls back on any exception
                print()
                record_set.data.to_sql(name=table.name, schema = table.layer, con=conn, if_exists="append", index=False)

            print(f"Loaded {len(record_set.data)} rows into {table.layer}.{table.name}")

        except ProgrammingError as e:
            print(f"Table or schema not found — check that {table.layer}.{table.name} exists and is deployed, or change the schema/table name in config.py:\n\r {e}")
            raise
        except DataError as e:
            print(f"Data truncation or type error during insert (value too long/wrong type) make sure to call validate_csv before loading:\n\r {e}")
            raise
        except OperationalError as e:
            print(f"Connection lost during insert:\n\r {e}")
            raise
        except IntegrityError as e:
            print(f"Constraint violation during insert:\n\r {e}")
            raise
        except Exception as e:
            print(f"Unexpected database error during insert:\n\r {e}")
            raise

    def getTable(self, layer: str, table_name: str)-> DatabaseTable:
        for t in self.tablesList:  
            if t.layer.lower() == layer.lower() and t.name.lower() == table_name.lower():
             return t
        raise KeyError(f"No table found for layer={layer}, name={table_name}")