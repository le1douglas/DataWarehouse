# the column rule: a locked column is never editable, whatever the row
def is_locked_column(column: str) -> bool:
    return column in {"row_id", "date_time"}


# the row rule: a row with a known error in audit is shown in red. every row stays editable
def is_error_row(errors: list[dict]) -> bool:
    return bool(errors)


# the descriptions of the errors in the whole row, those that name no column: every cell of the row shows them
def row_errors(errors: list[dict]) -> list[str]:
    return [error["description"] for error in errors if not error["target_column"]]


# the cell rule: a column of the row that an error names is shown in a stronger red, and only its cells show the
# descriptions of its errors
def column_errors(errors: list[dict]) -> dict[str, list[str]]:
    by_column: dict[str, list[str]] = {}
    for error in errors:
        if error["target_column"]:
            by_column.setdefault(error["target_column"], []).append(error["description"])
    return by_column


# the error rows out of view, as indexes in the grid: those above the shown pixels and those below. a row partly in
# view counts as in view. the rows are as high as each other and in the order they were sent: the grid neither sorts
# nor filters
def error_rows_out_of_view(
    error_indexes: list[int], top: float, bottom: float, row_height: float
) -> tuple[list[int], list[int]]:
    above = [index for index in error_indexes if (index + 1) * row_height <= top]
    below = [index for index in error_indexes if index * row_height >= bottom]
    return above, below


# a count of rows as text: 1 row, 2 rows
def rows_text(count: int) -> str:
    return f"{count} {'row' if count == 1 else 'rows'}"
