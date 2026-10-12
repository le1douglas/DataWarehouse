from functools import partial
from pathlib import Path

from datawarehouse import record_set
from datawarehouse.brnz_record_journal_entries import BrnzRecordJournalEntries

from datawarehouse.config import (
    DATASET_JOURNAL_ENTRIES,
    JOURNAL_ENTRIES_CSV,
    KEY_JOURNAL_ENTRIES,
    POSTGRES_CONFIG,
    SHEET_CORRECTIONS,
    SHEET_META_CORRECTIONS,
    TBL_BRNZ_JOURNAL_ENTRIES,
    TBL_CORR_JOURNAL_ENTRIES,
    TBL_META_BRONZE,
    TBL_META_CORRECTIONS,
)
from datawarehouse.corr_record_journal_entries import CorrRecordJournalEntries
from datawarehouse.loader import Loader
from datawarehouse.meta_record import MetaRecord
from datawarehouse.reader_csv import CSVReader
from datawarehouse.reader_excel import ExcelReader
from datawarehouse.record_set import RecordSet
from datawarehouse.sql_postgres_database import PostgreSQLDatabase


# csv -> dev_bronze
def load_bronze():
    filepath = JOURNAL_ENTRIES_CSV
    record_set = Loader.load(filepath, CSVReader, BrnzRecordJournalEntries)

    print(record_set.rows[0])


    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_bronze(TBL_BRNZ_JOURNAL_ENTRIES, record_set) 


# excel -> dev_corrections
def load_corrections():
    filepath = Path("C:\\Users\\TeeltQ-Farms\\OneDrive - Q-Farms\\Bureaublad\\journal_entries_corrections.xlsx")



def main():
    load_bronze()
    #load_corrections()


if __name__ == "__main__":
    main()
