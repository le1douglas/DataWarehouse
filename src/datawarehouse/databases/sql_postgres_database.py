from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, ProgrammingError

from datawarehouse.config import DB_SCHEMA_BRONZE, TBL_META_BRONZE
from datawarehouse.records.record_set import RecordSet


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

    # bronze only ever appends: row_id is assigned by the database, so a row is never already there
    def load_to_bronze(self, table_name: str, record_set: RecordSet):
        self._load(DB_SCHEMA_BRONZE, table_name, TBL_META_BRONZE, record_set)

    # meta_table_name is the meta table of the layer, i.e. "meta_bronze"
    def _load(self, layer: str, table_name: str, meta_table_name: str, record_set: RecordSet):

        try:
            # reads the columns of the tables from the database
            table = Table(table_name, MetaData(), schema=layer, autoload_with=self.engine)
            meta_table = Table(meta_table_name, MetaData(), schema=layer, autoload_with=self.engine)

            # RecordSet holds validated objects
            # Convert them to a list of dictionaries
            rows = [row.model_dump() for row in record_set.rows]

            # every row is inserted, a primary key that already exists fails the load
            statement = insert(table)
            meta_statement = insert(meta_table)

            # row_id is assigned by the database and handed back. sort_by_parameter_order hands the ids back
            # in the order the rows were sent, so the n-th id belongs to the n-th row
            # this also means every row is inserted individually and not as a batch operation. should be fine for the volume of data
            statement = statement.returning(table.c.row_id, sort_by_parameter_order=True)

            # one transaction: either every row and its metadata is loaded or nothing is
            with self.engine.begin() as conn:
                row_ids = conn.execute(statement, rows).scalars().all()

                # the only thing the metadata still needs is the row_id of its row
                meta_rows = [
                    {"row_id": row_id, **meta_record.model_dump()}
                    for row_id, row in zip(row_ids, record_set.rows, strict=True)
                    for meta_record in row.meta_records
                ]

                # the rows exist by now, so the metadata can reference them
                if meta_rows:
                    conn.execute(meta_statement, meta_rows)

            print(f"Loaded {len(record_set.rows)} rows into {layer}.{table_name}")
            print(f"Loaded {len(meta_rows)} rows into {layer}.{meta_table_name}")

        except ProgrammingError as e:
            print(f"Table or schema not found. Check that {layer}.{table_name} exists:\n\r{e}")
            raise
        except DataError as e:
            print(f"Data type or data value error during load:\n\r{e}")
            raise
        except OperationalError as e:
            print(f"Connection lost during load:\n\r{e}")
            raise
        except IntegrityError as e:
            print(f"Constraint violation during load:\n\r{e}")
            raise
        except Exception as e:
            print(f"Unexpected database error during load:\n\r{e}")
            raise
