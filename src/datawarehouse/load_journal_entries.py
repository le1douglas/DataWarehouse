

from datawarehouse.config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, TBL_JOURNAL_ENTRIES

from datawarehouse.sql_server_database import SQLServerDatabase
from datawarehouse.bronze_record_set import BronzeRecordSet
from datawarehouse.bronze_record_journal_entries import BronzeRecordJournalEntries
from datawarehouse.bronze_loader import BronzeLoader
from datawarehouse.reader_csv import CSVReader



def main():
   
    filepath = JOURNAL_ENTRIES_CSV
    record_set = BronzeLoader.load(filepath, CSVReader, BronzeRecordJournalEntries)


    db = SQLServerDatabase(DB_SERVER, DB_NAME)
    db.connect()
    db.load_to_bronze(TBL_JOURNAL_ENTRIES, record_set)



if __name__ == "__main__":
    main()
   
