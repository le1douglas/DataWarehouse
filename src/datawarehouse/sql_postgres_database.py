from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, ProgrammingError

from datawarehouse.config import DB_DEV_SCHEMA_BRONZE, DB_DEV_SCHEMA_CORRECTIONS, TBL_META_BRONZE
from datawarehouse.record_set import RecordSet


class PostgreSQLDatabase:
    def __init__(self, db_server: str, db_name: str, db_user: str, db_password: str, db_port: int):

        self.server = db_server
        self.name = db_name
        self.user = db_user
        self.port = db_port

        connection_string = f"postgresql+psycopg://{db_user}:{db_password}@{db_server}:{db_port}/{db_name}"

        self.engine: Engine = create_engine(connection_string)

    def connect(self):
        print(f'Connecting to database "{self.name}" on server "{self.server}:{self.port}"...')

        try:
            with self.engine.connect() as connection:
                print("Connection successful")
        except OperationalError as e:
            print(
                f'Could not reach the PostgreSQL server (check that server "{self.server}" exists, is running, and there are no network/firewall issues):\n\r{e}'
            )
            raise
        except Exception as e:
            print(f'Unknown exception occurred while connecting to "{self.server}":\n\r{e}')
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
                result = conn.execute(query, {"layer": layer, "table_name": table_name})
                return result.first() is not None
        except Exception as e:
            print(f'An error occurred while checking if table "{layer}.{table_name}" exists:\n\r{e}')
            raise

    # key_columns are the columns that identify a row, i.e. ["date_time", "subject"]
    def load_to_dev_corrections(self, table_name: str, record_set: RecordSet, key_columns: list[str]):
        self._upsert(DB_DEV_SCHEMA_CORRECTIONS, table_name, record_set, key_columns)

    def _upsert(self, layer: str, table_name: str, record_set: RecordSet, key_columns: list[str]):

        if not self.table_exists(layer, table_name):
            raise ValueError(f'Table "{table_name}" does not exist in layer "{layer}"')

        # RecordSet holds validated objects
        # Convert them to a list of dictionaries
        rows = [row.model_dump() for row in record_set.rows]

        try:
            # reads the columns of the table from the database
            table = Table(table_name, MetaData(), schema=layer, autoload_with=self.engine)

            # a row whose key is already in the table replaces the existing row,
            # the others are inserted
            statement = insert(table).values(rows)
            statement = statement.on_conflict_do_update(
                index_elements=key_columns,
                set_={
                    column.name: statement.excluded[column.name]
                    for column in table.columns
                    if column.name not in key_columns
                },
            )

            # one transaction: either every row is loaded or none is
            with self.engine.begin() as conn:
                conn.execute(statement)

            print(f"Upserted {len(rows)} rows into {layer}.{table_name}")

        except ProgrammingError as e:
            print(f"Table or schema not found. Check that {layer}.{table_name} exists:\n\r{e}")
            raise
        except DataError as e:
            print(f"Data type or data value error during upsert:\n\r{e}")
            raise
        except OperationalError as e:
            print(f"Connection lost during upsert:\n\r{e}")
            raise
        except IntegrityError as e:
            print(f"Constraint violation during upsert:\n\r{e}")
            raise
        except Exception as e:
            print(f"Unexpected database error during upsert:\n\r{e}")
            raise

    # meta_table_name is the meta table of the layer, i.e. "meta_bronze"
    def load_to_dev_bronze(self, table_name: str, record_set: RecordSet):
        self._load_to_bronze(DB_DEV_SCHEMA_BRONZE, table_name, TBL_META_BRONZE, record_set)

    def _load_to_bronze(self, layer: str, table_name: str, meta_table_name: str, record_set: RecordSet):

        for name in (table_name, meta_table_name):
            if not self.table_exists(layer, name):
                raise ValueError(f'Table "{name}" does not exist in layer "{layer}"')

        try:
            # reads the columns of the tables from the database
            table = Table(table_name, MetaData(), schema=layer, autoload_with=self.engine)
            meta_table = Table(meta_table_name, MetaData(), schema=layer, autoload_with=self.engine)

            meta_rows = []

            # one transaction: either every row and its metadata is loaded or nothing is
            with self.engine.begin() as conn:
                # row_id is assigned by the database, so every row is inserted on its own and
                # hands back its row_id. The metadata of the row is paired with it right here,
                # while the row is still at hand: there is nothing to match afterwards
                for row in record_set.rows:
                    statement = insert(table).values(row.model_dump()).returning(table.c.row_id)
                    row_id = conn.execute(statement).scalar_one()

                    for meta_record in row.meta_records:
                        meta_rows.append({"row_id": row_id,  **meta_record.model_dump()})

                # the bronze rows exist by now, so the metadata can reference them
                if meta_rows:
                    conn.execute(insert(meta_table), meta_rows)

            print(f"Loaded {len(record_set.rows)} rows into {layer}.{table_name}")
            print(f"Loaded {len(meta_rows)} rows into {layer}.{meta_table_name}")

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
