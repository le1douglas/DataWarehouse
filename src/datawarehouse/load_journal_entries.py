

from datawarehouse.config import  JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, POSTGRES_CONFIG, TBL_JOURNAL_ENTRIES

from datawarehouse.sql_postgres_database import PostgreSQLDatabase
from datawarehouse.bronze_record_set import BronzeRecordSet
from datawarehouse.bronze_record_journal_entries import BronzeRecordJournalEntries
from datawarehouse.bronze_loader import BronzeLoader
from datawarehouse.reader_csv import CSVReader


def main():
   
    filepath = JOURNAL_ENTRIES_CSV
    record_set = BronzeLoader.load(filepath, CSVReader, BronzeRecordJournalEntries)


    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_dev_bronze(TBL_JOURNAL_ENTRIES, record_set)



if __name__ == "__main__":
    main()
   
