import pandas as pd
import pandas as pd
from pathlib import Path


from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, DataError, IntegrityError

from datawarehouse.bronze_record_set import BronzeRecordSet

from datawarehouse.config import DB_SCHEMA_BRONZE


class SQLServerDatabase:

    def __init__(self, db_server: str, db_name: str):
     
        self.server = db_server
        self.name = db_name
        connection_string =  (f"mssql+pyodbc://{self.server}/{self.name}"
                                "?driver=ODBC+Driver+18+for+SQL+Server"
                                "&trusted_connection=yes"
                                "&TrustServerCertificate=yes")
        self.engine: Engine = create_engine(connection_string)

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

    def table_exists(self, layer: str, table_name: str) -> bool:
        query = text("""
            SELECT 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = :layer AND TABLE_NAME = :table_name
        """)
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"layer": layer, "table_name": table_name})
                return result.first() is not None
        except Exception as e:
            print(f"An error occurred while checking if table \"{layer}.{table_name}\" exists:\n\r {e}")
            raise

    def load_to_bronze(self, table_name: str, record_set: BronzeRecordSet):

        layer = DB_SCHEMA_BRONZE

        #todo add check if table exists in database at layer bronze
        if not self.table_exists(layer, table_name):
            raise ValueError(f"Table \"{table_name}\" does not exists in layer \"{layer}\"")

        # BronzeRecordSet holds validated JournalEntryRow  we want dataframe instead
        df = pd.DataFrame([row.model_dump() for row in record_set.rows])

        try:
            with self.engine.begin() as conn:
                df.to_sql(name=table_name, schema=layer, con=conn, if_exists="append", index=False)

            print(f"Loaded {len(df)} rows into {layer}.{table_name}")

        except ProgrammingError as e:
            print(f"Table or schema not found, check that {layer}.{table_name} exists and is deployed, or change the schema/table name in config.py:\n\r {e}")
            raise
        except DataError as e:
            print(f"Data truncation or type error during insert (value too long/wrong type):\n\r {e}")
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