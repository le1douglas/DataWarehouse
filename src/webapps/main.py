from nicegui import events, run, ui

from webapps.errors_tooltip import ErrorsTooltip
from webapps.grid import GRID_CSS, GRID_JS, grid_options
from webapps.logic import rows_text
from webapps.queries import select_aud_errors, select_cand_as_corr, select_datasets, upsert_corrections

# a placeholder until the app knows who is logged in
REVIEWER = "Claude"


@ui.page("/")
async def index():
    # the queries block, so they run in a thread instead of freezing the page for every user
    datasets = await run.io_bound(select_datasets)

    # the rows edited since the dataset was shown or last submitted, by row_id: a row edited twice is kept once, as it
    # is now
    edited_rows: dict[str, dict] = {}

    # the event carries the whole row after the edit
    def on_cell_edited(event: events.GenericEventArguments) -> None:
        row = event.args["data"]
        edited_rows[row["row_id"]] = row
        show_edited_count()

    # the submit button counts the edited rows, so a reviewer sees there is something to submit: Submit (1 row)
    def show_edited_count() -> None:
        count = len(edited_rows)
        if count == 0:
            submit_button.set_text("Submit")
        else:
            submit_button.set_text(f"Submit ({rows_text(count)})")

    # the page content is a column as high as the window, and the grid takes all of it below the top row
    ui.query(".nicegui-content").classes("h-screen")

    # the dataset on the left, the dark mode switch and the submit button on the right. the grid follows the page's
    # dark mode by itself
    with ui.row().classes("w-full justify-between items-center"):
        dataset_select = ui.select(datasets, label="Dataset", on_change=lambda e: show_dataset(e.value)).classes("w-64")
        with ui.row().classes("items-center"):
            ui.switch("Dark mode").bind_value(ui.dark_mode(True))
            submit_button = ui.button("Submit", on_click=lambda: submit())
    errors_tooltip = ErrorsTooltip()
    grid = ui.aggrid(grid_options([], [], {}, errors_tooltip)).classes("w-full flex-grow")
    grid.on("cellValueChanged", on_cell_edited)
    ui.add_css(GRID_CSS)
    ui.add_body_html(GRID_JS)

    # the grid is updated in place: the columns change with the dataset, so all its options are replaced.
    # edits not submitted are dropped with the dataset they belong to
    async def show_dataset(dataset: str) -> None:
        columns, rows = await run.io_bound(select_cand_as_corr, dataset)
        aud_errors = await run.io_bound(select_aud_errors, dataset)
        edited_rows.clear()
        show_edited_count()
        grid.options.update(grid_options(columns, rows, aud_errors, errors_tooltip))
        grid.update()

    # the dataset is shown again after a submit: the grid shows candidate as it is now, with the corrections, and no
    # cell is edited any more
    async def submit() -> None:
        if not edited_rows:
            ui.notify("Nothing to submit")
            return
        await run.io_bound(upsert_corrections, dataset_select.value, list(edited_rows.values()), REVIEWER)
        ui.notify(f"Submitted {rows_text(len(edited_rows))}", type="positive")
        await show_dataset(dataset_select.value)

    # the first dataset is shown when the page opens. setting the value calls show_dataset
    if datasets:
        dataset_select.set_value(datasets[0])


# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # show=False: there is no browser in the container to open
    ui.run(title="Corrections", show=False)
