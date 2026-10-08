from pathlib import Path

from datawarehouse.brnz_loader import BrnzLoader
from datawarehouse.brnz_record_journal_entries import BrnzRecordJournalEntries
from datawarehouse.config import (
    JOURNAL_ENTRIES_CSV,
    KEY_JOURNAL_ENTRIES,
    POSTGRES_CONFIG,
    TBL_BRNZ_JOURNAL_ENTRIES,
    TBL_CORR_JOURNAL_ENTRIES,
)
from datawarehouse.corr_loader import CorrLoader
from datawarehouse.corr_record_journal_entries import CorrRecordJournalEntries
from datawarehouse.reader_csv import CSVReader
from datawarehouse.reader_excel import ExcelReader
from datawarehouse.sql_postgres_database import PostgreSQLDatabase


# csv -> dev_bronze
def load_bronze():
    filepath = JOURNAL_ENTRIES_CSV
    record_set = BrnzLoader.load(filepath, CSVReader, BrnzRecordJournalEntries)

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_bronze(TBL_BRNZ_JOURNAL_ENTRIES, record_set)


# excel -> dev_corrections
def load_corrections():
    filepath = Path("C:\\Users\\TeeltQ-Farms\\OneDrive - Q-Farms\\Bureaublad\\journal_entries_corrections.xlsx")
    record_set = CorrLoader.load(filepath, ExcelReader, CorrRecordJournalEntries)

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_corrections(TBL_CORR_JOURNAL_ENTRIES, record_set, KEY_JOURNAL_ENTRIES)


def main():
    # load_bronze()
    load_corrections()


if __name__ == "__main__":
    main()
