"""Entry point of the package: run with `python -m datawarehouse bronze` or `python -m datawarehouse corrections`."""

import argparse

from datawarehouse.config import (
    CORRECTIONS_SHEET,
    CORRECTIONS_WORKBOOK,
    JOURNAL_ENTRIES_CSV,
    POSTGRES_CONFIG,
    TBL_BRNZ_JOURNAL_ENTRIES,
    TBL_CORR_JOURNAL_ENTRIES,
)
from datawarehouse.databases.sql_postgres_database import PostgreSQLDatabase
from datawarehouse.loaders.loader import Loader
from datawarehouse.readers.reader_csv import CSVReader
from datawarehouse.readers.reader_excel import ExcelReader
from datawarehouse.records.brnz_record_journal_entries import BrnzRecordJournalEntries
from datawarehouse.records.corr_record_journal_entries import CorrRecordJournalEntries


# csv -> dev_bronze
def load_bronze() -> None:
    df_csv = CSVReader.read(JOURNAL_ENTRIES_CSV)
    record_set = Loader.load(df_csv, BrnzRecordJournalEntries)
    print(record_set.rows[0])

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_bronze(TBL_BRNZ_JOURNAL_ENTRIES, record_set)


# excel -> dev_corrections
def load_corrections() -> None:
    df_excel = ExcelReader.read(CORRECTIONS_WORKBOOK, sheet=CORRECTIONS_SHEET)
    record_set = Loader.load(df_excel, CorrRecordJournalEntries)
    print(record_set.rows[0])

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_corrections(TBL_CORR_JOURNAL_ENTRIES, record_set)










LOADS = {
    "bronze": load_bronze,
    "corrections": load_corrections,
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m datawarehouse", description="Load one input of the warehouse.")
    parser.add_argument("load", choices=LOADS, help="bronze: csv -> dev_bronze, corrections: excel -> dev_corrections")
    args = parser.parse_args()
    LOADS[args.load]()


if __name__ == "__main__":
    main()
