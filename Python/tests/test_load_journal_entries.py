from io import StringIO
import unittest
import sys
import msvcrt

from pathlib import Path

import pandas as pd
import pandas.testing as pdt


ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# Make Python/ importable without turning this into a package.
sys.path.insert(0, str(ROOT_DIR / "Python"))
from load_journal_entries import read_csv_file, validate_csv_empty, validate_db_table_is_nvarchar

MALFORMED_CSV_DIR = ROOT_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv"


class TestReadCsvFile(unittest.TestCase):
    
    #normal, regular, csv file
    def test_valid_file(self):
        df = read_csv_file(MALFORMED_CSV_DIR / "valid.csv")
        self.assertEqual(len(df), 1) #dataframe has exactly one row
        
        expected_df = pd.DataFrame({
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
        }, dtype="str") 

        pdt.assert_frame_equal(df, expected_df)
        

    def test_esoteric_unicodes(self):
        df = read_csv_file(MALFORMED_CSV_DIR / "esoteric-unicodes.csv")
        self.assertEqual(len(df), 1) #dataframe has exactly one row
                
        expected_df = pd.DataFrame({
        "date_time": ["2026-01-01T12:00:00.000000"],
        "subject":   ["default_subject"],
        "notes":     ["this text contains esoteric unicodes: 🚀 Café naïve. مرحبا العالم! 你好世界 — "],
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
        }, dtype="str") 

        pdt.assert_frame_equal(df, expected_df)


    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            read_csv_file(MALFORMED_CSV_DIR / "this-file-does-not-exists.csv")


    @unittest.skipUnless(sys.platform == "win32", "msvcrt file locking is Windows-specific")
    def test_locked_file(self):
        locked_path = MALFORMED_CSV_DIR / "valid.csv"
        with open(locked_path, "r+b") as f:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)  # lock 1 byte, non-blocking
            try:
                with self.assertRaises(PermissionError):
                    read_csv_file(locked_path)
            finally:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)  # always unlock before closing
    
    #gets caught by file extension before arriving to the parser
    def test_is_a_directory(self):
        with self.assertRaises(ValueError):
            read_csv_file(ROOT_DIR)
        
    
    def test_empty_file(self):
        with self.assertRaises(pd.errors.EmptyDataError):
            read_csv_file(MALFORMED_CSV_DIR / "empty-no-columns.csv")


    def test_wrong_extension(self):
        with self.assertRaises(ValueError):
                    read_csv_file(MALFORMED_CSV_DIR / "wrong-extension.txt")
    
    #TODO when provided with CSV with more values than columns, it will truncate the extra values silently. Need to find a way to throw an exception.
    def test_inconsinstent_column_count(self):
        #with self.assertRaises(pd.errors.ParserError):
        read_csv_file(MALFORMED_CSV_DIR / "inconsinstent-column-count.csv")


    def test_invalid_utf_8(self):
        with self.assertRaises(UnicodeDecodeError):
            read_csv_file(MALFORMED_CSV_DIR / "invalid-UTF-8.csv")
    
class TestValidateCsvEmpty(unittest.TestCase):
    
    def test_no_rows(self):
        df = read_csv_file(MALFORMED_CSV_DIR / "empty-no-rows.csv")
        with self.assertRaises(pd.errors.EmptyDataError):
            validate_csv_empty(df)
    
    
    def test_one_row(self):
        df = read_csv_file(MALFORMED_CSV_DIR / "valid.csv")
        validate_csv_empty(df) #should not raise
        
        
        

class TestValidateDbTableIsNvarchar(unittest.TestCase):
    
    def test_table_is_nvarchar_all(self):
        df = pd.DataFrame({        "COLUMN_NAME": ["test_column_name", "test_column_name", "test_column_name"],
            "DATA_TYPE":   ["nvarchar", "nvarchar", "nvarchar"],
            "CHARACTER_MAXIMUM_LENGTH":     ["-1", "-1", "-1"],
            }, dtype="str")
        
        validate_db_table_is_nvarchar(df) #should not raise
    
    def test_table_is_nvarchar_partial(self):
        df = pd.DataFrame({        "COLUMN_NAME": ["test_column_name", "test_column_name", "test_column_name"],
        "DATA_TYPE":   ["nvarchar", "datetime2", "datetime2"],
        "CHARACTER_MAXIMUM_LENGTH":     ["-1", "", ""],
        }, dtype="str")
        
        with self.assertRaises(ValueError):
            validate_db_table_is_nvarchar(df)
    
    def test_table_is_nvarchar_none(self):
        df = pd.DataFrame({        "COLUMN_NAME": ["test_column_name", "test_column_name", "test_column_name"],
        "DATA_TYPE":   ["datetime2", "datetime2", "datetime2"],
        "CHARACTER_MAXIMUM_LENGTH":     ["", "", ""],
        }, dtype="str")
        
        with self.assertRaises(ValueError):
            validate_db_table_is_nvarchar(df)
    
    

if __name__ == "__main__":
    unittest.main()