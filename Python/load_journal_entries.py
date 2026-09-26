

from config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, TBL_JOURNAL_ENTRIES

from sql_server_database import SQLServerDatabase
from bronze_record_set import BronzeRecordSet
from csv_reader import CSVReader



def main():

    db = SQLServerDatabase(DB_SERVER, DB_NAME)
    db.connect()
    tbl = db.getTable(DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES)

    
    
    filepath = JOURNAL_ENTRIES_CSV
    csv_df = CSVReader().read(filepath)

    record_set = BronzeRecordSet(csv_df, str(filepath))

    if record_set.validate(tbl):
        db.load_to_bronze(table=tbl, record_set=record_set)
        pass
    

if __name__ == "__main__":
    main()
   
