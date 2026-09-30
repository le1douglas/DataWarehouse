
import pandas as pd

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError, DataError, IntegrityError

from datawarehouse.bronze_record_set import BronzeRecordSet
from datawarehouse.config import DB_SCHEMA_BRONZE


class PostgreSQLDatabase:

    def __init__(self,
                 db_server: str,
                db_name: str,
                db_user: str,
                db_password: str,
                db_port: int):
        
        self.server = db_server
        self.name = db_name
        self.user = db_user
        self.port = db_port

        connection_string = (
            f"postgresql+psycopg://"
            f"{db_user}:{db_password}@"
            f"{db_server}:{db_port}/"
            f"{db_name}"
        )

        self.engine: Engine = create_engine(connection_string)

    def connect(self):
        print(f"Connecting to database \"{self.name}\" on server \"{self.server}:{self.port}\"...")

        try:
            with self.engine.connect() as connection:
                print("Connection successful")
        except OperationalError as e:
            print(f"Could not reach the PostgreSQL server (check that server \"{self.server}\" exists, is running, and there are no network/firewall issues):\n\r{e}")
            raise
        except Exception as e:
            print(f"Unknown exception occurred while connecting to \"{self.server}\":\n\r{e}")
            raise

    def table_exists(self, layer: str, table_name: str) -> bool:

   

        query = text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :layer
              AND table_name = :table_name
        """)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(query,{"layer": layer,"table_name": table_name})
                return result.first() is not None
        except Exception as e:
            print(f"An error occurred while checking if table \"{layer}.{table_name}\" exists:\n\r{e}")
            raise

    def load_to_bronze(self, table_name: str, record_set: BronzeRecordSet):
        layer = DB_SCHEMA_BRONZE

        if not self.table_exists(layer, table_name):
            raise ValueError(f"Table \"{table_name}\" does not exist in layer \"{layer}\"")

        # BronzeRecordSet holds validated JournalEntryRow objects
        # Convert them to a DataFrame
        df = pd.DataFrame([row.model_dump() for row in record_set.rows])

        try:
            with self.engine.begin() as conn:
                df.to_sql(
                    name=table_name,
                    schema=layer,
                    con=conn,
                    if_exists="append",
                    index=False,
                )

            print(f"Loaded {len(df)} rows into {layer}.{table_name}")

        except ProgrammingError as e:
            print(f"Table or schema not found. Check that {layer}.{table_name} exists:\n\r{e}")
            raise
        except DataError as e:
            print(f"Data type or data value error during insert:\n\r{e}")
            raise
        except OperationalError as e:
            print(f"Connection lost during insert:\n\r{e}")
            raise
        except IntegrityError as e:
            print(f"Constraint violation during insert:\n\r{e}")
            raise
        except Exception as e:
            print(f"Unexpected database error during insert:\n\r{e}")
            raise