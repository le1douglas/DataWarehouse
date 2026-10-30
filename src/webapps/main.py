from nicegui import app, run, ui

from webapps.orchestration import run_ended, start_run_end_listener
from webapps.queries import select_aud_errors, select_cand_as_corr, select_datasets
from webapps.ui_elements.grid import Grid
from webapps.ui_elements.reload_button import ReloadButton
from webapps.ui_elements.submit_button import SubmitButton

app.on_startup(start_run_end_listener)


@ui.page("/")
async def index():
    # the queries block, so they run in a thread instead of freezing the page for every user
    datasets = await run.io_bound(select_datasets)

    # the page content is a column as high as the window, and the grid takes all of it below the top row
    ui.query(".nicegui-content").classes("h-screen")

    # the dataset on the left, the dark mode switch and the submit button on the right. the grid follows the page's
    # dark mode by itself. the reload button needs a dataset to show
    with ui.row().classes("w-full justify-between items-center"):
        dataset_select = ui.select(datasets, label="Dataset", on_change=lambda e: show_dataset(e.value)).classes("w-64")
        with ui.row().classes("items-center"):
            ui.switch("Dark mode").bind_value(ui.dark_mode(True))
            reload_button = ReloadButton(on_reload=lambda: show_dataset(dataset_select.value)).bind_enabled_from(
                dataset_select, "value", backward=bool
            )
            submit_button = SubmitButton(
                get_dataset=lambda: dataset_select.value,
                on_saved=lambda dataset: show_dataset(dataset),
                has_errors=lambda: grid.has_errors,
            )
    grid = Grid(on_row_edited=submit_button.add_edit)

    # edits not submitted are dropped with the dataset they belong to
    async def show_dataset(dataset: str) -> None:
        columns, rows = await run.io_bound(select_cand_as_corr, dataset)
        aud_errors = await run.io_bound(select_aud_errors, dataset)
        submit_button.clear_edits()
        reload_button.show_current()
        grid.show_rows(columns, rows, aud_errors)

    # a dbt command has ended, so candidate and audit may have changed. a page without edits shows the dataset again at
    # once, and tells whether it still has errors; a page with edits keeps them, and marks the reload button instead
    async def on_run_end(command: str) -> None:
        if not dataset_select.value:
            return
        if submit_button.has_edits:
            reload_button.show_outdated()
            return
        await show_dataset(dataset_select.value)
        if grid.has_errors:
            ui.notify(f"dbt {command} has ended: some rows still have errors", type="warning")
        else:
            ui.notify(f"dbt {command} has ended: no more errors", type="positive")

    run_ended.subscribe(on_run_end)

    # the first dataset is shown when the page opens. setting the value calls show_dataset
    if datasets:
        dataset_select.set_value(datasets[0])


# __mp_main__: the reload process of ui.run imports this module under that name
if __name__ in {"__main__", "__mp_main__"}:
    # show=False: there is no browser in the container to open
    ui.run(title="Corrections", show=False)
