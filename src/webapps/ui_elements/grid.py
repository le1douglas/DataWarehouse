import json
from collections.abc import Callable

from nicegui import ui

from webapps.ui_elements.error_jump_buttons import ErrorJumpButtons
from webapps.ui_elements.errors_tooltip import ErrorsTooltip

# pixels
MIN_COLUMN_WIDTH = 120

# a cell that cannot be edited is grayed out, in the colors of the theme: those of the header and of secondary text.
# on an error row its background stays transparent, so the red of the row shows through
LOCKED_CELL_STYLE = (
    "{backgroundColor: params.data.is_error_row ? 'transparent' : 'var(--ag-chrome-background-color)', "
    "color: 'var(--ag-subtle-text-color)', cursor: 'not-allowed'}"
)

# a row with a known error has the theme's background of a row edited with an invalid value: its invalid color mixed
# onto the background, light enough to read the text in both modes
ERROR_ROW_STYLE = "{backgroundColor: 'var(--ag-full-row-edit-invalid-background-color)'}"

# a cell that an error names has the theme's invalid color at half strength, so it stands out in its red row and its
# text stays readable. it is mixed onto the background, as the theme mixes its own tints, so it is solid: the full
# color is never a background in the theme, and it has no text color to go on it
ERROR_CELL_COLOR = "color-mix(in srgb, var(--ag-invalid-color) 60%, var(--ag-background-color))"
ERROR_CELL_STYLE = f"{{backgroundColor: '{ERROR_CELL_COLOR}'}}"

# a button over the grid has the red of an error cell. the vars are only defined inside the grid's .ag-root-wrapper,
# so the button has to be in it
ERROR_BUTTON_STYLE = f"background-color: {ERROR_CELL_COLOR}; color: var(--ag-text-color)"

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


# the grid where a reviewer corrects a dataset, with its errors tooltip and its error jump buttons. on_row_edited gets
# the whole row after each edit
class Grid(ui.aggrid):
    def __init__(self, on_row_edited: Callable[[dict], None]) -> None:
        errors_tooltip = ErrorsTooltip()
        super().__init__(_grid_options([], [], errors_tooltip))
        self.classes("w-full flex-grow")
        self._errors_tooltip = errors_tooltip
        self._error_jump_buttons = ErrorJumpButtons(self, ERROR_BUTTON_STYLE)
        self.on("cellValueChanged", lambda e: on_row_edited(e.args["data"]))
        ui.add_css(GRID_CSS)
        ui.add_body_html(GRID_JS)

    @property
    def has_errors(self) -> bool:
        return self._error_jump_buttons.has_errors

    # the grid is updated in place: the columns change with the dataset, so all its options are replaced
    def show_rows(self, columns: list[str], rows: list[dict], aud_errors: dict[str, list[dict]]) -> None:
        row_data = [_row_data(row, aud_errors) for row in rows]
        error_indexes = [index for index, row in enumerate(row_data) if row["is_error_row"]]
        self._error_jump_buttons.set_error_indexes(error_indexes)
        self.options.update(_grid_options(columns, row_data, self._errors_tooltip))
        self.update()


# the options of ui.aggrid
def _grid_options(columns: list[str], row_data: list[dict], errors_tooltip: ErrorsTooltip) -> dict:
    return {
        "columnDefs": [_column_def(column) for column in columns],
        # flex: the columns share the window width, down to MIN_COLUMN_WIDTH, then the grid scrolls sideways
        "defaultColDef": {"resizable": True, "sortable": False, "flex": 1, "minWidth": MIN_COLUMN_WIDTH},
        **errors_tooltip.grid_handlers(),
        ":onCellValueChanged": "params => markEdited(params)",
        "rowData": row_data,
        ":getRowId": "params => params.data.row_id",
        ":getRowStyle": f"params => params.data.is_error_row ? {ERROR_ROW_STYLE} : null",
    }


# a locked column is not editable and grayed out, every other cell is editable and outlined once edited. a cell that
# an error names is red on top: a locked one keeps its gray text and cursor
def _column_def(column: str) -> dict:
    is_error_cell = f"({json.dumps(column)} in params.data.column_errors)"
    error_style = f"...({is_error_cell} ? {ERROR_CELL_STYLE} : {{}})"
    if _is_locked_column(column):
        locked_style = f"...{LOCKED_CELL_STYLE}"
        return {"field": column, "editable": False, ":cellStyle": f"params => ({{{locked_style}, {error_style}}})"}
    is_edited_cell = f"params.data.edited_columns.includes({json.dumps(column)})"
    edited_style = f"...({is_edited_cell} ? {EDITED_CELL_STYLE} : {NOT_EDITED_CELL_STYLE})"
    return {"field": column, "editable": True, ":cellStyle": f"params => ({{{edited_style}, {error_style}}})"}


# the row and cell rules and the errors are decided once here and sent with the row: is_error_row, row_errors,
# column_errors and edited_columns have no column, so the grid does not show them. ErrorsTooltip shows a cell the
# row_errors and the column_errors of its column, and markEdited fills edited_columns
def _row_data(row: dict, aud_errors: dict[str, list[dict]]) -> dict:
    errors = aud_errors.get(row["row_id"], [])
    return row | {
        "is_error_row": bool(errors),
        "row_errors": _row_errors(errors),
        "column_errors": _column_errors(errors),
        "edited_columns": [],
    }


# the column rule: a locked column is never editable, whatever the row
def _is_locked_column(column: str) -> bool:
    return column in {"row_id", "date_time"}


# the descriptions of the errors in the whole row, those that name no column: every cell of the row shows them
def _row_errors(errors: list[dict]) -> list[str]:
    return [error["description"] for error in errors if not error["target_column"]]


# the cell rule: a column of the row that an error names is shown in a stronger red, and only its cells show the
# descriptions of its errors
def _column_errors(errors: list[dict]) -> dict[str, list[str]]:
    by_column: dict[str, list[str]] = {}
    for error in errors:
        if error["target_column"]:
            by_column.setdefault(error["target_column"], []).append(error["description"])
    return by_column
