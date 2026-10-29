from webapps.logic import is_locked_column, is_locked_row

# pixels
MIN_COLUMN_WIDTH = 120

# a cell that cannot be edited is grayed out, in the colors of the theme: those of the header and of secondary text
LOCKED_CELL_STYLE = (
    "{backgroundColor: 'var(--ag-chrome-background-color)', color: 'var(--ag-subtle-text-color)', cursor: 'not-allowed'}"
)

# the default theme with columnBorder: true. nicegui only takes a theme by name, so the parameter is set as its css
# variable, with the value true stands for: a line in the theme's border color. it goes on .ag-root-wrapper, the
# element where the theme defines --ag-border-color: set on the grid element, outside it, the var would be empty
GRID_CSS = ".ag-root-wrapper { --ag-column-border: solid 1px var(--ag-border-color); }"


# the options of ui.aggrid
def grid_options(columns: list[str], rows: list[dict]) -> dict:
    return {
        "columnDefs": [column_def(column) for column in columns],
        # flex: the columns share the window width, down to MIN_COLUMN_WIDTH, then the grid scrolls sideways
        "defaultColDef": {"resizable": True, "sortable": False, "flex": 1, "minWidth": MIN_COLUMN_WIDTH},
        "rowData": [row_data(row) for row in rows],
        ":getRowId": "params => params.data.row_id",
    }


def column_def(column: str) -> dict:
    return {"field": column, ":editable": editable_rule(column), ":cellStyle": cell_style_rule(column)}


# the row rule is decided once here and sent with the row: is_locked_row has no column, so the grid does not show it
def row_data(row: dict) -> dict:
    return row | {"is_locked_row": is_locked_row(row)}


# a javascript function: the column rule is decided here, the row rule is read from the row
def editable_rule(column: str) -> str:
    if is_locked_column(column):
        return "params => false"
    return "params => !params.data.is_locked_row"


# a javascript function giving the style of a cell, with the same rules as editable_rule
def cell_style_rule(column: str) -> str:
    if is_locked_column(column):
        return f"params => ({LOCKED_CELL_STYLE})"
    return f"params => params.data.is_locked_row ? {LOCKED_CELL_STYLE} : null"
