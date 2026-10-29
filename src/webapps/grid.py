from webapps.logic import is_error_row, is_locked_column

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

# the default theme with columnBorder: true. nicegui only takes a theme by name, so the parameter is set as its css
# variable, with the value true stands for: a line in the theme's border color. it goes on .ag-root-wrapper, the
# element where the theme defines --ag-border-color: set on the grid element, outside it, the var would be empty.
# .row-errors is the box of ROW_ERRORS_JS, in the colors of the theme's tooltip, bordered in the red of an error row,
# one error per line. it is fixed at the pointer and lets the mouse through to the cell below
GRID_CSS = (
    ".ag-root-wrapper { --ag-column-border: solid 1px var(--ag-border-color); } "
    ".row-errors { position: fixed; z-index: 1000; pointer-events: none; white-space: pre-line; padding: 4px 8px; "
    "background-color: var(--ag-tooltip-background-color); color: var(--ag-tooltip-text-color); "
    "border: solid 1px var(--ag-invalid-color); border-radius: var(--ag-border-radius); }"
)

# one box for the errors of the row under the pointer, instead of the grid's tooltips: the grid gives every cell its
# own tooltip, and swapping it from cell to cell flickered. this box stays open from cell to cell, only its text and
# position change. it goes inside .ag-root-wrapper, where the theme's variables are defined
ROW_ERRORS_JS = """
<script>
function rowErrorsBox(wrapper) {
    let box = document.getElementById('row-errors');
    if (!box) {
        box = document.createElement('div');
        box.id = 'row-errors';
        box.className = 'row-errors';
        box.hidden = true;
    }
    if (wrapper && box.parentElement !== wrapper) wrapper.appendChild(box);
    return box;
}
function moveRowErrors(event) {
    const box = rowErrorsBox();
    box.style.left = event.clientX + 12 + 'px';
    box.style.top = event.clientY + 12 + 'px';
}
function showRowErrors(params) {
    const box = rowErrorsBox(params.event.target.closest('.ag-root-wrapper'));
    box.textContent = params.data.errors || '';
    box.hidden = !params.data.errors;
    moveRowErrors(params.event);
}
function hideRowErrors() {
    rowErrorsBox().hidden = true;
}
document.addEventListener('mousemove', moveRowErrors);
</script>
"""


# the options of ui.aggrid
def grid_options(columns: list[str], rows: list[dict], aud_errors: dict[str, list[str]]) -> dict:
    return {
        "columnDefs": [column_def(column) for column in columns],
        # flex: the columns share the window width, down to MIN_COLUMN_WIDTH, then the grid scrolls sideways
        "defaultColDef": {"resizable": True, "sortable": False, "flex": 1, "minWidth": MIN_COLUMN_WIDTH},
        # the box of ROW_ERRORS_JS shows the errors of the row under the pointer: a row without errors shows none
        ":onCellMouseOver": "params => showRowErrors(params)",
        ":onCellMouseOut": "params => hideRowErrors()",
        "rowData": [row_data(row, aud_errors) for row in rows],
        ":getRowId": "params => params.data.row_id",
        ":getRowStyle": f"params => params.data.is_error_row ? {ERROR_ROW_STYLE} : null",
    }


# a locked column is not editable and grayed out, every other cell is editable
def column_def(column: str) -> dict:
    if is_locked_column(column):
        return {"field": column, "editable": False, ":cellStyle": f"params => ({LOCKED_CELL_STYLE})"}
    return {"field": column, "editable": True}


# the row rule and the errors, one per line, are decided once here and sent with the row: is_error_row and errors have
# no column, so the grid does not show them
def row_data(row: dict, aud_errors: dict[str, list[str]]) -> dict:
    errors = "\n".join(aud_errors.get(row["row_id"], [])) or None
    return row | {"is_error_row": is_error_row(row, aud_errors), "errors": errors}
