"""Entry point of the package: run with `python -m datawarehouse bronze`."""

import argparse

from datawarehouse.config import (
    JOURNAL_ENTRIES_CSV,
    POSTGRES_CONFIG,
    TBL_BRNZ_JOURNAL_ENTRIES,
    TIMEZONE,
)
from datawarehouse.databases.sql_postgres_database import PostgreSQLDatabase
from datawarehouse.loaders.loader import Loader
from datawarehouse.readers.reader_csv import CSVReader
from datawarehouse.records.brnz_record_journal_entries import BrnzRecordJournalEntries


# csv -> bronze
def load_bronze() -> None:
    df_csv = CSVReader.read(JOURNAL_ENTRIES_CSV, TIMEZONE)
    record_set = Loader.load(df_csv, BrnzRecordJournalEntries)
    print(record_set.rows[0])

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_bronze(TBL_BRNZ_JOURNAL_ENTRIES, record_set)


LOADS = {
    "bronze": load_bronze,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m datawarehouse", description="Load one input of the warehouse.")
    parser.add_argument("load", choices=LOADS, help="bronze: csv -> bronze")
    args = parser.parse_args()
    LOADS[args.load]()


if __name__ == "__main__":
    main()
