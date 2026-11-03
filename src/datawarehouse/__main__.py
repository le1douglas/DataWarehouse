"""Entry point of the package: run with `python -m datawarehouse bronze`."""

import argparse
import sys

from datawarehouse.config import (
    DBT_SELECT_JOURNAL_ENTRIES,
    JOURNAL_ENTRIES_CSV,
    POSTGRES_CONFIG,
    TBL_BRNZ_JOURNAL_ENTRIES,
)
from datawarehouse.databases.sql_postgres_database import PostgreSQLDatabase
from datawarehouse.loaders.loader import Loader, UploadRefused
from datawarehouse.loaders.upload import upload
from datawarehouse.readers.reader_csv import CSVReader
from datawarehouse.records.brnz_record_journal_entries import BrnzRecordJournalEntries


# csv -> bronze -> dbt build, or the file is refused and nothing stays in bronze
def load_bronze() -> None:
    try:
        df_csv = CSVReader.read(JOURNAL_ENTRIES_CSV)
        record_set = Loader.load(df_csv, BrnzRecordJournalEntries)

        postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
        postgres.connect()
        upload(postgres, TBL_BRNZ_JOURNAL_ENTRIES, record_set, DBT_SELECT_JOURNAL_ENTRIES)
    except UploadRefused as refused:
        print(refused)
        sys.exit(1)


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
