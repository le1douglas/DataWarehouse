
import unittest
import sys

from pathlib import Path

import pandas as pd
import pandas.testing as pdt


ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Make Python/ importable without turning this into a package.
sys.path.insert(0, str(ROOT_DIR / "Python"))


from config import DB_SCHEMA_BRONZE
from database_table import DatabaseTable
from Python.reader_csv import CSVReader
from bronze_record_set import BronzeRecordSet

MALFORMED_CSV_DIR = ROOT_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv"

   
class TestDatabaseTable_ValidateDbTableIsNvarchar(unittest.TestCase):

    def setUp(self):
         self.db_table = DatabaseTable(
                    DB_SCHEMA_BRONZE, 
                    "db_table_name",
                    pd.DataFrame({
                        "COLUMN_NAME": [
                                "date_time", "subject", "notes", "type", "ec",
                                "ec_pore", "ec_bulk", "ph", "mc", "temp",
                                "device", "media", "tags"
                            ],
                        "DATA_TYPE": [
                                "nvarchar", "nvarchar", "nvarchar", "nvarchar", "nvarchar",
                                "nvarchar", "nvarchar", "nvarchar", "nvarchar", "nvarchar",
                                "nvarchar", "nvarchar", "nvarchar"
                            ],
                        "CHARACTER_MAXIMUM_LENGTH": [
                                100, 100, 100, 100, 100, 100, 100,
                                    100, 100, 100, 100, 100, 100
                            ],
                        })
                )
    
    def test_table_is_nvarchar_all(self):
        self.db_table._validate_table_is_nvarchar() #should not raise
    
    def test_table_is_nvarchar_partial(self):
        #change the 2nd and 3rd row to datetime

        self.db_table.schema_with_debug_columns.loc[1:2, "DATA_TYPE"] = "datetime2"
        self.db_table.schema_with_debug_columns.loc[1:2, "CHARACTER_MAXIMUM_LENGTH"] = pd.NA
        
        with self.assertRaises(ValueError):
            self.db_table._validate_table_is_nvarchar()

    def test_table_is_nvarchar_none(self):
        #change the 1st, 2nd and 3rd row to datetime
        self.db_table.schema_with_debug_columns.loc[0:2, "DATA_TYPE"] = "datetime2"
        self.db_table.schema_with_debug_columns.loc[0:2, "CHARACTER_MAXIMUM_LENGTH"] = pd.NA
                
        with self.assertRaises(ValueError):
           self.db_table._validate_table_is_nvarchar()


if __name__ == "__main__":
    unittest.main()