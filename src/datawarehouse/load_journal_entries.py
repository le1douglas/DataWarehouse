

from datawarehouse.config import  DB_SCHEMA_BRONZE, JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, POSTGRES_CONFIG, MICROSOFT_SQL_CONFIG, TBL_JOURNAL_ENTRIES

from datawarehouse.sql_postgres_database import PostgreSQLDatabase
from datawarehouse.sql_server_database import SQLServerDatabase
from datawarehouse.bronze_record_set import BronzeRecordSet
from datawarehouse.bronze_record_journal_entries import BronzeRecordJournalEntries
from datawarehouse.bronze_loader import BronzeLoader
from datawarehouse.reader_csv import CSVReader

#TODO see if .egg-info can be put in .gitignore 

def main():
   
    filepath = JOURNAL_ENTRIES_CSV
    record_set = BronzeLoader.load(filepath, CSVReader, BronzeRecordJournalEntries)


    #db = SQLServerDatabase(**MICROSOFT_SQL_CONFIG)
    #db.connect()
    #db.load_to_bronze(TBL_JOURNAL_ENTRIES, record_set)


    postgres = PostgreSQLDatabase(**POSTGRES_CONFIG)
    postgres.connect()
    postgres.load_to_bronze(TBL_JOURNAL_ENTRIES, record_set)



if __name__ == "__main__":
    main()
   
