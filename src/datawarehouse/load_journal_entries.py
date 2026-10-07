

from pathlib import Path

from datawarehouse.config import  JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, KEY_JOURNAL_ENTRIES, POSTGRES_CONFIG, TBL_JOURNAL_ENTRIES

from datawarehouse.corrections_loader import CorrectionsLoader
from datawarehouse.corrections_records_journal_entries import CorrectionsRecordJournalEntries
from datawarehouse.reader_excel import ExcelReader
from datawarehouse.sql_postgres_database import PostgreSQLDatabase
from datawarehouse.bronze_record_journal_entries import BronzeRecordJournalEntries
from datawarehouse.bronze_loader import BronzeLoader
from datawarehouse.reader_csv import CSVReader


#csv -> dev_bronze
def load_bronze():
    filepath = JOURNAL_ENTRIES_CSV
    record_set = BronzeLoader.load(filepath, CSVReader, BronzeRecordJournalEntries)

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_bronze(TBL_JOURNAL_ENTRIES, record_set)


#excel -> dev_corrections
def load_corrections():
    filepath = Path("C:\\Users\\TeeltQ-Farms\\OneDrive - Q-Farms\\Bureaublad\\journal_entries_corrections.xlsx")
    record_set = CorrectionsLoader.load(filepath, ExcelReader, CorrectionsRecordJournalEntries)

    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_corrections(TBL_JOURNAL_ENTRIES, record_set, KEY_JOURNAL_ENTRIES)


def main():
    #load_bronze()
    load_corrections()

if __name__ == "__main__":
    main()

