import pandas as pd
import csv
from pathlib import Path

class CSVReader:

    def __init__(self):
        pass


    def read(self, source: Path) -> pd.DataFrame:
        print(f"Loading CSV file: {source}")

        #check that the file has a .csv extension, case insensitive
        if source.suffix.lower() != ".csv":
            raise ValueError(f"Expected a CSV file, got: {source.suffix}")

        try:
            df = pd.read_csv(source, 
                dtype=object,   # every cell is a plain Python object, no assuptions about the type.
                delimiter=',', 
                quotechar="\"",
                on_bad_lines='error', #as soon as you encounter a problem, throw an exception
                keep_default_na=False, #dont assume "N/A", "n/a", "null" etc are null values. 
                na_values=[""], # instead only assume "" is null
                index_col=False) #no extra colmns with panda's index

            #change pd.notna into None
            df = df.where(pd.notna(df), None)
            
            self._validate_fields_number_equals_columns_number(source)
            
            print(f"Loaded {len(df)} rows")
            return df

        except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
            print(f"Error opening CSV file; check that the file exists and is not already opened by another program: {e}")
            raise
        except pd.errors.EmptyDataError as e:
            print(f"CSV file is empty: {e}")
            raise
        except (pd.errors.ParserError, UnicodeDecodeError) as e:
            print(f"Error parsing CSV file; check that the file is a valid CSV and is encoded as UTF-8: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred while reading the CSV file:\n\r {e}")
            raise


    # check if the number of fields in every row matches the column counts
    # only validation made at this level, because it's necessary for creating a valid dataframe. Is considered a parsing error
    # TODO find a way to do it in panda
    def _validate_fields_number_equals_columns_number(self, csv_path: Path):
            with csv_path.open(newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if row and len(row) != len(header): # 'row' is [] for a blank line, pandas skips those too
                        raise pd.errors.ParserError("CSV has a row whose number of fields differs from the header")
