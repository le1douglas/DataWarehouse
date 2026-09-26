
import datetime
from pathlib import Path
import pandas as pd

from database_table import DatabaseTable


class BronzeRecordSet:
    def __init__(self, data: pd.DataFrame, source: str):
        self._data = data
        self._source = source
        self._load_time = pd.Timestamp.now(datetime.timezone.utc)
        self._add_debug_columns()
        print(self.data)

    def _add_debug_columns(self) -> None:
        self.data["_extract_date_time"] = self.load_time
        self.data["_source"] = self.source


    @property
    def data(self) -> pd.DataFrame:
        return self._data

    @property
    def source(self) -> str:
        return self._source

    @property
    def load_time(self) -> pd.Timestamp:
        return self._load_time


    #make initial validation checks on the source before loading it into the database
    #returns true if validation is passed, false otherwise.
    def validate(self, target_table: DatabaseTable) -> bool:
        try :
            self._validate_is_not_empty()
            self._validate_columns_names_and_number(target_table)
            self._validate_max_string_lenght(target_table)
            return True

        except pd.errors.EmptyDataError as e:
            print(f"Source \"{self.source}\" is empty:\n\r {e}")
            return False
        except ValueError as e:
            print(f"Source \"{self.source}\" has a schema mismatch, columns don't match target table:\n\r {e}")
            return False
        except Exception as e:
            print(f"Source \"{self.source}\" had un unexpected error during validation:\n\r {e}")
            return False


    # check if any of the columns contains a string that exceeds the max length defined in the schema
    # WARNING this assumes that all the columns in the target table are nvarchar
    # WARNING this assumes every column in target table is present in the source

    def _validate_max_string_lenght(self, target_table: DatabaseTable):

        max_sizes_df = target_table.schema.set_index("COLUMN_NAME")["CHARACTER_MAXIMUM_LENGTH"]
        max_sizes_df = max_sizes_df[max_sizes_df != -1] # nvarchar(MAX) has a max length of -1 in the schema, no need to check length for these columns

        for col_name, max_length in max_sizes_df.items():
            source_max_lenght = self.data[col_name].str.len().max()
            if source_max_lenght > max_length: 
                raise ValueError(f"Column \"{col_name}\" in \"{self.source}\" has at least one value that exceeds max length of {max_length} defined in target table schema. Max length is {source_max_lenght}.")           

    #make sure the columns are what we expect them to be, both in number an name
    def _validate_columns_names_and_number(self, target_table: DatabaseTable):
        expected_columns = set(target_table.schema_with_debug_columns["COLUMN_NAME"])
        actual_columns = set(self.data.columns)

        missing = expected_columns - actual_columns
        extra = actual_columns - expected_columns

        if len(missing) > 0:
            raise ValueError(f"Source \"{self.source}\" is missing expected columns: {missing}")
        if len(extra) > 0:
            raise ValueError(f"Source \"{self.source}\" has unexpected extra columns: {extra}")


    def _validate_is_not_empty(self):
        if len(self.data) == 0:
            raise pd.errors.EmptyDataError(f"Source \"{self.source}\" has columns names, but has no rows") #columns are present, but no rows of data


