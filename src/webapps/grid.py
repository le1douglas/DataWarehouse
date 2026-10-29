import json

from webapps.errors_tooltip import ErrorsTooltip
from webapps.logic import column_errors, is_error_row, is_locked_column, row_errors

# pixels
MIN_COLUMN_WIDTH = 120

# a cell that cannot be edited is grayed out, in the colors of the theme: those of the header and of secondary text.
# on an error row its background stays transparent, so the red of the row shows through
LOCKED_CELL_STYLE = (
    "{backgroundColor: params.data.is_error_row ? 'transparent' : 'var(--ag-chrome-background-color)', "
    "color: 'var(--ag-subtle-text-color)', cursor: 'not-allowed'}"
)

# a row with a known error is tinted with the theme's invalid color, the red of an invalid cell, light enough to read
# the text in both modes
ERROR_ROW_STYLE = "{backgroundColor: 'color-mix(in srgb, var(--ag-invalid-color) 20%, transparent)'}"

# a cell that an error names is tinted with the same red, stronger, so it stands out in its red row
ERROR_CELL_STYLE = "{backgroundColor: 'color-mix(in srgb, var(--ag-invalid-color) 50%, transparent)'}"

# a cell edited since the dataset was shown or last submitted has a dashed outline in the theme's range selection
# color, the accent. an outline, not a border: it takes no room and leaves the cell's own border to the grid's focus.
# none is set too: the grid keeps a style property a cell had until a new style sets it again
EDITED_CELL_STYLE = "{outline: '2px dashed var(--ag-range-selection-border-color)', outlineOffset: '-3px'}"
NOT_EDITED_CELL_STYLE = "{outline: 'none'}"

# the default theme with columnBorder: true. nicegui only takes a theme by name, so the parameter is set as its css
# variable, with the value true stands for: a line in the theme's border color. it goes on .ag-root-wrapper, the
# element where the theme defines --ag-border-color: set on the grid element, outside it, the var would be empty
GRID_CSS = ".ag-root-wrapper { --ag-column-border: solid 1px var(--ag-border-color); }"

# the javascript the grid options call.
# markEdited records the column of an edited cell in the row, and redraws the cell so its style shows it
GRID_JS = """
<script>
function markEdited(params) {
    const columns = params.data.edited_columns;
    if (!columns.includes(params.colDef.field)) columns.push(params.colDef.field);
    params.api.refreshCells({rowNodes: [params.node], columns: [params.column], force: true});
}
</script>
"""


# the options of ui.aggrid
def grid_options(
    columns: list[str], rows: list[dict], aud_errors: dict[str, list[dict]], errors_tooltip: ErrorsTooltip
) -> dict:
    return {
        "columnDefs": [column_def(column) for column in columns],
        # flex: the columns share the window width, down to MIN_COLUMN_WIDTH, then the grid scrolls sideways
        "defaultColDef": {"resizable": True, "sortable": False, "flex": 1, "minWidth": MIN_COLUMN_WIDTH},
        **errors_tooltip.grid_handlers(),
        ":onCellValueChanged": "params => markEdited(params)",
        "rowData": [row_data(row, aud_errors) for row in rows],
        ":getRowId": "params => params.data.row_id",
        ":getRowStyle": f"params => params.data.is_error_row ? {ERROR_ROW_STYLE} : null",
    }


# a locked column is not editable and grayed out, every other cell is editable and outlined once edited. a cell that
# an error names is red on top: a locked one keeps its gray text and cursor
def column_def(column: str) -> dict:
    is_error_cell = f"({json.dumps(column)} in params.data.column_errors)"
    error_style = f"...({is_error_cell} ? {ERROR_CELL_STYLE} : {{}})"
    if is_locked_column(column):
        locked_style = f"...{LOCKED_CELL_STYLE}"
        return {"field": column, "editable": False, ":cellStyle": f"params => ({{{locked_style}, {error_style}}})"}
    is_edited_cell = f"params.data.edited_columns.includes({json.dumps(column)})"
    edited_style = f"...({is_edited_cell} ? {EDITED_CELL_STYLE} : {NOT_EDITED_CELL_STYLE})"
    return {"field": column, "editable": True, ":cellStyle": f"params => ({{{edited_style}, {error_style}}})"}


# the row and cell rules and the errors are decided once here and sent with the row: is_error_row, row_errors,
# column_errors and edited_columns have no column, so the grid does not show them. ErrorsTooltip shows a cell the
# row_errors and the column_errors of its column, and markEdited fills edited_columns
def row_data(row: dict, aud_errors: dict[str, list[dict]]) -> dict:
    errors = aud_errors.get(row["row_id"], [])
    return row | {
        "is_error_row": is_error_row(errors),
        "row_errors": row_errors(errors),
        "column_errors": column_errors(errors),
        "edited_columns": [],
    }
