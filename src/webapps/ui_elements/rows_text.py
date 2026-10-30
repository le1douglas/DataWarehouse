# a count of rows as text: 1 row, 2 rows
def rows_text(count: int) -> str:
    return f"{count} {'row' if count == 1 else 'rows'}"
