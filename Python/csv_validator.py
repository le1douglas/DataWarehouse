import pandas as pd
from database_table import DatabaseTable

class CSVValidator:

    def __init__(self):
        pass


    #make initial validation checks on the CSV file before loading it into the database
    #returns true if validation is passed, false otherwise.
    def validate(self, csv_df: pd.DataFrame,  target_table: DatabaseTable) -> bool:
        try :
            self._validate_csv_empty(csv_df)
            self._validate_columns_names_and_number(csv_df, target_table)
            self._validate_max_string_lenght(csv_df, target_table)
            return True

        except pd.errors.EmptyDataError as e:
            print(f"CSV file is empty: {e}")
            return False
        except ValueError as e:
            print(f"Schema mismatch, CSV columns don't match target table: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred during CSV validation: {e}")
            raise
            return False


    #check if any of the columns in the CSV contains a string that exceeds the max length defined in the schema
    # WARNING this assumes that all the columns in the target table are nvarchar
    # WARNING this assumes every column in target table is present in the dataframe

    def _validate_max_string_lenght(self, df: pd.DataFrame, target_table: DatabaseTable):

        max_sizes_df = target_table.getSchema().set_index("COLUMN_NAME")["CHARACTER_MAXIMUM_LENGTH"]
        max_sizes_df = max_sizes_df[max_sizes_df != -1] # nvarchar(MAX) has a max length of -1 in the schema, no need to check length for these columns

        for col_name, max_length in max_sizes_df.items():
            csv_max_length = df[col_name].str.len().max()
            if csv_max_length > max_length: 
                raise ValueError(f"Column '{col_name}' in CSV has a value that exceeds max length of {max_length} defined in target table schema. Max length in CSV is {csv_max_length}.")           
            


    #make sure the columns are what we expect them to be, both in number an name
    def _validate_columns_names_and_number(self, df: pd.DataFrame, target_table: DatabaseTable):
        expected_columns = set(target_table.getSchema()["COLUMN_NAME"])
        actual_columns = set(df.columns)

        missing = expected_columns - actual_columns
        extra = actual_columns - expected_columns

        if len(missing) > 0:
            raise ValueError(f"CSV is missing expected columns: {missing}")
        if len(extra) > 0:
            raise ValueError(f"CSV has unexpected extra columns: {extra}")


    def _validate_csv_empty(self, df: pd.DataFrame):
        if len(df) == 0:
            raise pd.errors.EmptyDataError("CSV has columns names, but has no rows") #columns are present, but no rows of data
