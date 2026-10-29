import os
import random

from nicegui import events, run, ui
from sqlalchemy import create_engine, text

# the same variables as the loader. no defaults: a missing variable stops the app with a KeyError naming it
engine = create_engine(
    f"postgresql+psycopg://{os.environ['POSTGRESQL_USER']}:{os.environ['POSTGRESQL_PASSWORD']}"
    f"@{os.environ['POSTGRESQL_SERVER']}:{os.environ['POSTGRESQL_PORT']}/{os.environ['POSTGRESQL_DB']}"
)


# every value as text, like bronze itself: row_id is a uuid, which the browser cannot receive as is
def read_bronze() -> tuple[list[str], list[dict]]:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM dw_bronze.brnz_journal_entries"))
        columns = list(result.keys())
        rows = [
            {column: None if value is None else str(value) for column, value in row.items()}
            for row in result.mappings()
        ]

    return columns, rows


@ui.page("/")
async def index():
    # the query blocks, so it runs in a thread instead of freezing the page for every user
    columns, rows = await run.io_bound(read_bronze) or ([], [])

    # the page content is a column as high as the window, and the grid takes all of it below the label
    ui.query(".nicegui-content").classes("h-screen")

    ui.label("dw_bronze.brnz_journal_entries")
    ui.aggrid(
        {
            "columnDefs": [column_def(column) for column in columns],
            # flex: the columns share the window width, down to MIN_COLUMN_WIDTH, then the grid scrolls sideways
            "defaultColDef": {"resizable": True, "flex": 1, "minWidth": MIN_COLUMN_WIDTH},
            "rowData": [row_data(row) for row in rows],
            ":getRowId": "params => params.data.row_id",
        }
    ).classes("w-full flex-grow").style(
        # theme parameters of AG Grid, set as css variables: a line between columns, in the body and in the header
        f"--ag-column-border: {COLUMN_BORDER}; --ag-header-column-border: {COLUMN_BORDER}"
    ).on("cellValueChanged", on_cell_edited)


# pixels
MIN_COLUMN_WIDTH = 120

# the line between columns
COLUMN_BORDER = "solid 1px #d1d5db"

# a cell that cannot be edited is grayed out, in the colors of the theme: those of the header and of secondary text
LOCKED_CELL_STYLE = (
    "{backgroundColor: 'var(--ag-chrome-background-color)', color: 'var(--ag-subtle-text-color)', cursor: 'not-allowed'}"
)


def column_def(column: str) -> dict:
    return {"field": column, ":editable": editable_rule(column), ":cellStyle": cell_style_rule(column)}


# the row rule is decided once here and sent with the row: is_locked_row has no column, so the grid does not show it
def row_data(row: dict) -> dict:
    return row | {"is_locked_row": is_locked_row(row)}


# the column rule: a locked column is never editable, whatever the row
def is_locked_column(column: str) -> bool:
    return column in {"row_id", "date_time"}


# the row rule: a locked row is never editable, whatever the column. a random placeholder for now
def is_locked_row(_row: dict) -> bool:
    return random.choice([True, False])


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


def on_cell_edited(_event: events.GenericEventArguments) -> None:
    ui.notify("edited")


# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # show=False: there is no browser in the container to open
    ui.run(title="Corrections", show=False)
