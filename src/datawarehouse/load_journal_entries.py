from pathlib import Path

from datawarehouse.config import (
    JOURNAL_ENTRIES_CSV,
    POSTGRES_CONFIG,
    SHEET_CORRECTIONS,
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
def load_bronze():
    filepath = JOURNAL_ENTRIES_CSV
    df_csv = CSVReader.read(filepath)
    record_set = Loader.load(df_csv, BrnzRecordJournalEntries)

    print(record_set.rows[0])

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_bronze(TBL_BRNZ_JOURNAL_ENTRIES, record_set)


# excel -> dev_corrections
def load_corrections():
    filepath = Path("C:\\Users\\TeeltQ-Farms\\OneDrive - Q-Farms\\Bureaublad\\journal_entries_corrections.xlsx")
    df_excel = ExcelReader.read(filepath, sheet=SHEET_CORRECTIONS)
    corr_record_set = Loader.load(df_excel, CorrRecordJournalEntries)
    print(corr_record_set.rows[0])

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_corrections(TBL_CORR_JOURNAL_ENTRIES, corr_record_set)


def main():
    load_bronze()
    # load_corrections()


if __name__ == "__main__":
    main()
