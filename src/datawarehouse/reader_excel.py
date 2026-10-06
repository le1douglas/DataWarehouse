import pandas as pd
import csv
from pathlib import Path

class ExcelReader:

    def __init__(self):
        pass


    def read(self, source: Path) -> pd.DataFrame:
        print(f"Loading CSV file: {source}")

        self._validate_is_excel_file(source)
        df = pd.read_excel(source, sheet_name="corrected")
        
        #change pd.notna into None
        df = df.where(pd.notna(df), None)
            
        return pd.DataFrame(df)




    def _validate_is_excel_file(self, source: Path):
        #check that the file has a .csv extension, case insensitive
            if source.suffix.lower() != ".xlsx" :
                raise ValueError(f"Wrong file extension. Expected a Excel file, got: {source.suffix}")
