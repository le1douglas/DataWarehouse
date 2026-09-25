

from config import DB_NAME, DB_SCHEMA_BRONZE, DB_SERVER, JOURNAL_ENTRIES_CSV, JOURNAL_ENTRIES_MALFORMED_CSV, TBL_JOURNAL_ENTRIES

from sql_server_database import SQLServerDatabase
from csv_reader import CSVReader
from csv_validator import CSVValidator



def main():

    db = SQLServerDatabase(DB_SERVER, DB_NAME)
    db.connect()
    
    
    filepath = JOURNAL_ENTRIES_CSV


    csv_df = CSVReader().read(filepath)
    print(csv_df)

    tbl = db.getTable(DB_SCHEMA_BRONZE, TBL_JOURNAL_ENTRIES)


    if CSVValidator().validate(csv_df, tbl):
        #db.load_to_bronze(table=tbl, df=csv_df, original_file_path=filepath)
        pass
    

if __name__ == "__main__":
    main()
   
