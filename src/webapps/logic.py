# the column rule: a locked column is never editable, whatever the row
def is_locked_column(column: str) -> bool:
    return column in {"row_id", "date_time"}


# the row rule: a row with a known error in audit is shown in red. every row stays editable
def is_error_row(row: dict, aud_errors: dict[str, list[dict]]) -> bool:
    return row["row_id"] in aud_errors


# the cell rule: the columns of the row that an error names are shown in a stronger red. an error in the whole row
# names no column
def error_columns(row: dict, aud_errors: dict[str, list[dict]]) -> list[str]:
    return [error["target_column"] for error in aud_errors.get(row["row_id"], []) if error["target_column"]]
