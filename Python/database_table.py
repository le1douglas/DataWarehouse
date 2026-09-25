

import pandas as pd
from sqlalchemy import text



class DatabaseTable:
    
    def __init__(self, layer: str, name: str, schema: pd.DataFrame):
         self.layer = layer
         self.name = name
         self.schema = schema
         pass
     
    def isBronze(self) -> bool:
         #check schema layer
         #check is nvarchar
         return True

    
    def _validate_table_is_nvarchar(self, db_table_schema_df: pd.DataFrame):
        if not (db_table_schema_df["DATA_TYPE"] == "nvarchar").all():  # all columns must be nvarchar
                raise ValueError(f"All columns in the database table must be of type nvarchar (with the exception of debug columns that start with an underscore)")


    def getSchema(self, includeDebugColumns=False) -> pd.DataFrame:
          if includeDebugColumns:
               return self.schema
          return self.schema[~self.schema["COLUMN_NAME"].str.startswith("_")]

    def getLayer(self) -> str:
         return self.layer

    def getName(self) -> str:
         return self.name
         
