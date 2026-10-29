import os

from nicegui import run, ui
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
    columns, rows = await run.io_bound(read_bronze)

    ui.table(
        columns=[{"name": column, "label": column, "field": column} for column in columns],
        rows=rows,
        row_key="row_id",
        title="dw_bronze.brnz_journal_entries",
    ).props("flat bordered")


# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # show=False: there is no browser in the container to open
    ui.run(title="Corrections", show=False)
