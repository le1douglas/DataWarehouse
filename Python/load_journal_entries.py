

from config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, TBL_JOURNAL_ENTRIES

from sql_server_database import SQLServerDatabase
from bronze_record_set import BronzeRecordSet
from bronze_record_journal_entries import BronzeRecordJournalEntries
from bronze_loader import BronzeLoader
from reader_csv import CSVReader



def main():

    db = SQLServerDatabase(DB_SERVER, DB_NAME)
    db.connect()
    
    
    filepath = JOURNAL_ENTRIES_CSV



    record_set = BronzeLoader.load(filepath, CSVReader, BronzeRecordJournalEntries)
    db.load_to_bronze(TBL_JOURNAL_ENTRIES, record_set)

    

if __name__ == "__main__":
    main()
   
