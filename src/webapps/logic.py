# the column rule: a locked column is never editable, whatever the row
def is_locked_column(column: str) -> bool:
    return column in {"row_id", "date_time"}


# the row rule: a row with a known error in audit is shown in red. every row stays editable
def is_error_row(row: dict, aud_errors: dict[str, list[str]]) -> bool:
    return row["row_id"] in aud_errors
