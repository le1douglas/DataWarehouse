from uuid import UUID

from sqlalchemy import MetaData, Row, Table, create_engine, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, ProgrammingError

from datawarehouse.config import DB_SCHEMA_AUDIT, DB_SCHEMA_BRONZE, VW_AUD_FAILURES
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

    # bronze only ever appends: row_id is assigned by the database, so a row is never already there.
    # returns the row_id of every row, in the order of the record set
    def load_to_bronze(self, table_name: str, record_set: RecordSet) -> list[UUID]:
        return self._load(DB_SCHEMA_BRONZE, table_name, record_set)

    # the undo of a load that was refused
    def delete_from_bronze(self, table_name: str, row_ids: list[UUID]) -> None:
        table = Table(table_name, MetaData(), schema=DB_SCHEMA_BRONZE, autoload_with=self.engine)

        with self.engine.begin() as conn:
            conn.execute(delete(table).where(table.c.row_id.in_(row_ids)))

        print(f"Deleted {len(row_ids)} rows from {DB_SCHEMA_BRONZE}.{table_name}")

    # what failed in one dbt run
    def read_failures(self, invocation_id: str) -> list[Row]:
        view = Table(VW_AUD_FAILURES, MetaData(), schema=DB_SCHEMA_AUDIT, autoload_with=self.engine)
        statement = select(view.c.row_id, view.c.target_column, view.c.description).where(
            view.c.invocation_id == invocation_id
        )

        with self.engine.connect() as conn:
            return list(conn.execute(statement))

    def _load(self, layer: str, table_name: str, record_set: RecordSet) -> list[UUID]:

        try:
            # reads the columns of the table from the database
            table = Table(table_name, MetaData(), schema=layer, autoload_with=self.engine)

            # RecordSet holds validated objects
            # Convert them to a list of dictionaries
            rows = [row.model_dump() for row in record_set.rows]

            # every row is inserted, a primary key that already exists fails the load
            statement = insert(table)

            # row_id is assigned by the database and handed back. sort_by_parameter_order hands the ids back
            # in the order the rows were sent, so the n-th id belongs to the n-th row
            # this also means every row is inserted individually and not as a batch operation. should be fine for the volume of data
            statement = statement.returning(table.c.row_id, sort_by_parameter_order=True)

            # one transaction: either every row is loaded or nothing is
            with self.engine.begin() as conn:
                row_ids = conn.execute(statement, rows).scalars().all()

            print(f"Loaded {len(record_set.rows)} rows into {layer}.{table_name}")

            return row_ids

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
