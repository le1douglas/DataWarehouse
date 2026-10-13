from pathlib import Path

import pandas as pd


class ExcelReader:
    # returns two dataframes with the same rows in the same order:
    # the data, and the metadata the reviewer filled in (the last two columns of the sheet)
    @staticmethod
    def read(source: Path, sheet: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        print(f"Loading Excel file: {source}")

        ExcelReader._validate_is_excel_file(source)
        df = pd.read_excel(
            source,
            sheet_name=sheet,
            dtype=object,  # every cell is a plain Python object, no assuptions about the type.
            keep_default_na=False,  # dont assume "N/A", "n/a", "null" etc are null values.
            na_values=[""],  # instead only assume an empty cell is null
        )

        # change pd.notna into None
        df = df.astype(object).where(pd.notna(df), None)

        print(f"Loaded {len(df)} rows")

        # the split is by position, not by column name TODO
        data_df = df.iloc[:, :-2]
        meta_df = df.iloc[:, -2:]

        return data_df, meta_df

    @staticmethod
    def _validate_is_excel_file(source: Path):
        # check that the file has a .xlsx extension, case insensitive
        if source.suffix.lower() != ".xlsx":
            raise ValueError(f"Wrong file extension. Expected a Excel file, got: {source.suffix}")
