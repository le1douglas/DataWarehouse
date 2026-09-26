

import pandas as pd
from sqlalchemy import text

from config import DB_SCHEMA_BRONZE



class DatabaseTable:
    
     def __init__(self, layer: str, name: str, schema: pd.DataFrame):
          self._layer = layer
          self._name = name
          self._schema = schema
          if self.isBronze():
               self._validate_table_is_nvarchar()

     def isBronze(self):
          return  self.layer == DB_SCHEMA_BRONZE

     def isSilver(self):
          return  self.layer == DB_SCHEMA_SILVER

     def isGold(self):
               return  self.layer == DB_SCHEMA_GOLD

     @property
     def layer(self) -> str:
          return self._layer

     @property
     def name(self) -> str:
          return self._name

     @property
     def schema(self) -> pd.DataFrame:
          #take out all the debug columns that start with underscore
          return self._schema[~self._schema["COLUMN_NAME"].str.startswith("_")] 

     @property
     def schema_with_debug_columns(self) -> pd.DataFrame:
          return self._schema
     
    
     def _validate_table_is_nvarchar(self):
          if not (self.schema["DATA_TYPE"] == "nvarchar").all():  # all columns must be nvarchar
               raise ValueError(f"All columns of table \"{self.name}\" in layer \"{self.layer}\" must be of type nvarchar (with the exception of debug columns that start with an underscore)")