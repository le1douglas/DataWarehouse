import csv
from datetime import datetime
from pathlib import Path

import pandas as pd


class CSVReader:
    # returns two dataframes with the same rows in the same order:
    # the data, and the metadata of the read (from where and when every row was read)
    @staticmethod
    def read(source: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        print(f"Loading CSV file: {source}")

        CSVReader._validate_is_csv_file(source)

        try:
            df = pd.read_csv(
                source,
                dtype=object,  # every cell is a plain Python object, no assuptions about the type.
                delimiter=",",
                quotechar='"',
                on_bad_lines="error",  # as soon as you encounter a problem, throw an exception
                keep_default_na=False,  # dont assume "N/A", "n/a", "null" etc are null values.
                na_values=[""],  # instead only assume "" is null
                index_col=False,  # no extra colmns with panda's index
            )

            # change pd.notna into None
            df = df.where(pd.notna(df), None)

            CSVReader._validate_fields_number_equals_columns_number(source)

            print(f"Loaded {len(df)} rows")

            # the file has no metadata of its own, so it is made here.
            # the date and time has no time zone, is cut to the second and is the same for every row of the read
            meta_df = pd.DataFrame(
                {
                    "source_metadata": str(source),
                    "extract_date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                index=df.index,
                dtype=object,
            )

            return df, meta_df

        except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
            print(
                f"Error opening CSV file; check that the file exists and is not already opened by another program: {e}"
            )
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
    @staticmethod
    def _validate_fields_number_equals_columns_number(csv_path: Path):
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row and len(row) != len(header):  # 'row' is [] for a blank line, pandas skips those too
                    raise pd.errors.ParserError("CSV has a row whose number of fields differs from the header")

    @staticmethod
    def _validate_is_csv_file(source: Path):
        # check that the file has a .csv extension, case insensitive
        if source.suffix.lower() != ".csv":
            raise ValueError(f"Wrong file extension. Expected a CSV file, got: {source.suffix}")
