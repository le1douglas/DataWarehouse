
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
from csv_reader import CSVReader
from bronze_record_set import BronzeRecordSet

MALFORMED_CSV_DIR = ROOT_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv"

#TODO check that validate_csv returns false, rather then testing for a specific exception

#text fields sorrounded by text delimiter "": All should be valid
#text fields not sorrounded by text delimiter: Fails only when texts include field delimiters or new lines
class TestReadCsvFile_Fields(unittest.TestCase):

    # (file name, expected value of the "notes" column, expected exception when the same value is present without quotes around it); every file is otherwise identical to df_valid_csv
    TEST_CASES = [
    ("esoteric-unicodes.csv", "this text contains esoteric unicodes: 🚀 Café naïve. مرحبا العالم! 你好世界 — ",                      None),
    ("newline.csv",           "this text contains\n\ra carriage return and newline",                                                  pd.errors.ParserError), #breakes the rows in two, so it fails
    ("punctuation.csv",       "this text contains common punctuation except comma quotes and tab \\;!@#$%^&*()_+-=[]\\{\\}|;'^:./<>?€",  None),
    ("quotes.csv",            "this text contains \"escaped quotes",                                                                  None),
    ("tab.csv",               "this text contains\ta tab",                                                                            None),
    ("comma.csv",             "this text contains, a comma",                                                                          pd.errors.ParserError) # creates an extra field, so it breakes
    ]


    def setUp(self):
        
        # test against a well formed csv dataframe
        self.df_valid_csv = pd.DataFrame({
                "date_time": ["2026-01-01T12:00:00.000000"],
                "subject":   ["default_subject"],
                "notes":     ["default_notes"],
                "type":      ["measurement"],
                "ec":        ["1.00"],
                "ec_pore":   [pd.NA],
                "ec_bulk":   [pd.NA],
                "ph":        ["7.00"],
                "mc":        [pd.NA],
                "temp":      ["25.0"],
                "device":    [pd.NA],
                "media":     [pd.NA],
                "tags":      [pd.NA],
                }, dtype="str") #type string just like CSVReader().read

    def test_valid(self):
        df = CSVReader().read(MALFORMED_CSV_DIR / "valid.csv")
        self.assertEqual(len(df), 1)  # dataframe has exactly one row
        pdt.assert_frame_equal(df, self.df_valid_csv)


    #loop through every case in TEST_CASES
    def test_notes_special_characters(self):
        for file_name, expected_notes, expected_exception_when_unquoted in self.TEST_CASES:

            expected_df = self.df_valid_csv.copy()  # don't mutate the shared fixture
            expected_df["notes"] = expected_notes

            unquoted_file_name = Path(file_name).stem + "-unquoted.csv"

            with self.subTest(file=file_name):
                df = CSVReader().read(MALFORMED_CSV_DIR / file_name)
                self.assertEqual(len(df), 1)  # dataframe has exactly one row


                pdt.assert_frame_equal(df, expected_df)

            with self.subTest(file=unquoted_file_name):
                if expected_exception_when_unquoted is None:
                    df = CSVReader().read(MALFORMED_CSV_DIR / unquoted_file_name)
                    pdt.assert_frame_equal(df, expected_df)
                else:
                    with self.assertRaises(expected_exception_when_unquoted):
                        CSVReader().read(MALFORMED_CSV_DIR / unquoted_file_name)


#expected is UTF-8
class TestReadCsvFile_TextEncoding(unittest.TestCase):
    def setUp(self):
        self.df_valid_csv = pd.DataFrame({
                "date_time": ["2026-01-01T12:00:00.000000"],
                "subject":   ["default_subject"],
                "notes":     ["default_notes"],
                "type":      ["measurement"],
                "ec":        ["1.00"],
                "ec_pore":   [pd.NA],
                "ec_bulk":   [pd.NA],
                "ph":        ["7.00"],
                "mc":        [pd.NA],
                "temp":      ["25.0"],
                "device":    [pd.NA],
                "media":     [pd.NA],
                "tags":      [pd.NA],
                }, dtype="str") #type string just like CSVReader().read()

    def test_utf_8(self):
        df = CSVReader().read(MALFORMED_CSV_DIR / "valid.csv")
        self.assertEqual(len(df), 1)  # dataframe has exactly one row
        pdt.assert_frame_equal(df, self.df_valid_csv)

    def test_utf_8_bom(self):
        df = CSVReader().read(MALFORMED_CSV_DIR / "UTF-8-bom.csv")
        self.assertEqual(len(df), 1)  # dataframe has exactly one row
        pdt.assert_frame_equal(df, self.df_valid_csv)
    
    def test_invalid_utf_8(self):
        with self.assertRaises(UnicodeDecodeError):
            CSVReader().read(MALFORMED_CSV_DIR / "invalid-UTF-8.csv")

    def test_utf_16(self):
        with self.assertRaises(UnicodeDecodeError):
            CSVReader().read(MALFORMED_CSV_DIR / "UTF-16.csv")

    def test_valid_ANSI(self):
        with self.assertRaises(UnicodeDecodeError):
            CSVReader().read(MALFORMED_CSV_DIR / "valid-ANSI.csv")

#problems stemming from the file itself
class TestReadCsvFile_FileError(unittest.TestCase):

        
    def test_wrong_extension(self):
            with self.assertRaises(ValueError):
                CSVReader().read(MALFORMED_CSV_DIR / "wrong-extension.txt")
        


    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            CSVReader().read(MALFORMED_CSV_DIR / "this-file-does-not-exists.csv")

    #completely empty (0 bytes of text)
    def test_empty_file(self):
            with self.assertRaises(pd.errors.EmptyDataError):
                CSVReader().read(MALFORMED_CSV_DIR / "empty-no-columns.csv")
    
    @unittest.skipUnless(sys.platform == "win32", "msvcrt file locking is Windows-specific")
    def test_locked_file_win(self):
        import msvcrt  # imported here, not at module level, so non-Windows machines don't choke on it

        locked_path = MALFORMED_CSV_DIR / "valid.csv"
        with open(locked_path, "r+b") as f:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)  # lock 1 byte, non-blocking
            try:
                with self.assertRaises(PermissionError):
                    CSVReader().read(locked_path)
            finally:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)  # always unlock before closing


    #TODO unable to test on windows, find mac or linux to test it on
    @unittest.skipIf(sys.platform == "win32", "")
    def test_locked_file_posix(self):
        pass

    # A directory whose name ends in .csv passes the extension check, so pandas actually tries to open it as a file.
    @unittest.skipUnless(sys.platform == "win32", "PermissionError on directory is Windows-specific; POSIX raises IsADirectoryError instead")
    def test_directory_named_csv_win(self):
        directory_as_csv = MALFORMED_CSV_DIR / "not-a-real-file.csv"
        directory_as_csv.mkdir(exist_ok=True)
        try:
            with self.assertRaises(PermissionError):
                CSVReader().read(directory_as_csv)
        finally:
            directory_as_csv.rmdir()
                
        
    #TODO unable to test on windows, find mac or linux to test it on
    # A directory whose name ends in .csv passes the extension check, so pandas actually tries to open it as a file.
    @unittest.skipIf(sys.platform == "win32", "IsADirectoryError on directory is POSIX-specific; Windows raises PermissionError instead")
    def test_directory_named_csv_posix(self):
        directory_as_csv = MALFORMED_CSV_DIR / "not-a-real-file.csv"
        directory_as_csv.mkdir(exist_ok=True)
        try:
            with self.assertRaises(IsADirectoryError):
                CSVReader().read(directory_as_csv)
        finally:
            directory_as_csv.rmdir()  

class TestValidateFieldsNumberEqualsColumnNumber(unittest.TestCase):

    def test_extra_value(self):
        with self.assertRaises(pd.errors.ParserError):
            CSVReader().read(MALFORMED_CSV_DIR / "extra-value.csv")

    def test_missing_value(self):
        with self.assertRaises(pd.errors.ParserError):
            CSVReader().read(MALFORMED_CSV_DIR / "missing-value.csv")

class TestValidateBronzeRecordSet(unittest.TestCase):
    def setUp(self):
        self.db_table = DatabaseTable(
            DB_SCHEMA_BRONZE, 
            "db_table_name",
            pd.DataFrame({
                "COLUMN_NAME": [
                        "date_time", "subject", "notes", "type", "ec",
                        "ec_pore", "ec_bulk", "ph", "mc", "temp",
                        "device", "media", "tags", "_extract_date_time", "_source"
                    ],
                "DATA_TYPE": [
                        "nvarchar", "nvarchar", "nvarchar", "nvarchar", "nvarchar",
                        "nvarchar", "nvarchar", "nvarchar", "nvarchar", "nvarchar",
                        "nvarchar", "nvarchar", "nvarchar", "datetime2", "nvarchar"
                    ],
                "CHARACTER_MAXIMUM_LENGTH": [
                        50, 50, 400, 50, 50, 50, 50,
                            50, 50, 50, 50, 50, 50, pd.NA, 400 #TODO Check if datetime2 returns null
                    ],
                })
        )

    #helper to create a recordset from path
    def createRecordSet(self, path: Path) -> BronzeRecordSet:
            df = CSVReader().read(path)
            return BronzeRecordSet(df, str(path))
    


    # ----- _validate_columns_names_and_number ----
    def test_columns_valid(self):
        record_set = self.createRecordSet(MALFORMED_CSV_DIR / "valid.csv")
        record_set._validate_columns_names_and_number(self.db_table) #should not fail
    
    def test_column_missing(self):
        record_set = self.createRecordSet(MALFORMED_CSV_DIR / "missing-column.csv")
        with self.assertRaises(ValueError):
            record_set._validate_columns_names_and_number(self.db_table)

    def test_column_extra(self):
        record_set = self.createRecordSet(MALFORMED_CSV_DIR / "extra-column.csv")
        with self.assertRaises(ValueError):
            record_set._validate_columns_names_and_number(self.db_table)

    #debug columns start with underscore. Adding this test just in case we decide to handle them differently in the future
    def test_column_extra_with_underscore(self):
        record_set = self.createRecordSet(MALFORMED_CSV_DIR / "extra-column-underscore.csv")
        with self.assertRaises(ValueError):
            record_set._validate_columns_names_and_number(self.db_table)

    # -------  _validate_is_not_empty ------ 
    def test_one_row(self):
        record_set = self.createRecordSet( MALFORMED_CSV_DIR / "valid.csv")
        record_set._validate_is_not_empty() #should not raise


    def test_no_rows(self):
        record_set = self.createRecordSet( MALFORMED_CSV_DIR / "empty-no-rows.csv")
        with self.assertRaises(pd.errors.EmptyDataError):
            record_set._validate_is_not_empty()
    
    # -------  __validate_max_string_lenght ------ 
    def test_one_row(self):
        record_set = self.createRecordSet( MALFORMED_CSV_DIR / "valid.csv")
        record_set._validate_max_string_lenght(self.db_table) #should not raise



    def test_string_too_long(self):
        record_set = self.createRecordSet(MALFORMED_CSV_DIR / "long-string.csv")
        with self.assertRaises(ValueError):
            record_set._validate_max_string_lenght(self.db_table)
   


class TestValidateDbTableIsNvarchar(unittest.TestCase):

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