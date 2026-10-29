import random


# the column rule: a locked column is never editable, whatever the row
def is_locked_column(column: str) -> bool:
    return column in {"row_id", "date_time"}


# the row rule: a locked row is never editable, whatever the column. a random placeholder for now
def is_locked_row(_row: dict) -> bool:
    return random.choice([True, False])
