from pathlib import Path

import pandas as pd


class ExcelReader:
    # one reader reads one sheet: a workbook with several tables needs one reader per sheet
    def __init__(self, sheet_name: str):
        self.sheet_name = sheet_name

    def read(self, source: Path) -> pd.DataFrame:
        print(f'Loading Excel file: {source}, sheet "{self.sheet_name}"')

        self._validate_is_excel_file(source)
        df = pd.read_excel(
            source,
            sheet_name=self.sheet_name,
            dtype=object,  # every cell is a plain Python object, no assuptions about the type.
            keep_default_na=False,  # dont assume "N/A", "n/a", "null" etc are null values.
            na_values=[""],  # instead only assume an empty cell is null
        )

        # change pd.notna into None
        df = df.astype(object).where(pd.notna(df), None)

        print(f"Loaded {len(df)} rows")
        return df

    def _validate_is_excel_file(self, source: Path):
        # check that the file has a .xlsx extension, case insensitive
        if source.suffix.lower() != ".xlsx":
            raise ValueError(f"Wrong file extension. Expected a Excel file, got: {source.suffix}")
