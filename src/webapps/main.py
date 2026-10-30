from nicegui import events, run, ui

from webapps.errors_tooltip import ErrorsTooltip
from webapps.grid import ERROR_BUTTON_STYLE, GRID_CSS, GRID_JS, grid_options
from webapps.logic import error_rows_out_of_view, is_error_row, rows_text
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
    # over the grid, a button at the top and one at the bottom count the error rows out of view on that side. they are
    # teleported into the grid's .ag-root-wrapper, for the colors of its theme. the grid makes a new wrapper with every
    # dataset, so the teleport is updated once the rows are shown. color=None: the default primary is a quasar class
    # that is !important, and would cover the red of the style
    with ui.teleport(f"#{grid.html_id} .ag-root-wrapper") as buttons_teleport:
        above_button = (
            ui.button(icon="arrow_upward", color=None, on_click=lambda: jump_to(error_above[-1]))
            .props("rounded")
            .classes("absolute top-14 left-1/2 -translate-x-1/2 z-10")
            .style(ERROR_BUTTON_STYLE)
        )
        below_button = (
            ui.button(icon="arrow_downward", color=None, on_click=lambda: jump_to(error_below[0]))
            .props("rounded")
            .classes("absolute bottom-4 left-1/2 -translate-x-1/2 z-10")
            .style(ERROR_BUTTON_STYLE)
        )
    above_button.visible = False
    below_button.visible = False
    grid.on("cellValueChanged", on_cell_edited)

    # the indexes of the error rows of the dataset shown, and of those out of view above and below it
    error_indexes: list[int] = []
    error_above: list[int] = []
    error_below: list[int] = []

    # the buttons follow what the grid shows: after a scroll, a resize, or a new dataset
    async def show_out_of_view() -> None:
        pixels = await grid.run_grid_method("getVerticalPixelRange")
        sizes = await grid.run_grid_method("getSizesForCurrentTheme")
        above, below = error_rows_out_of_view(error_indexes, pixels["top"], pixels["bottom"], sizes["rowHeight"])
        error_above[:] = above
        error_below[:] = below
        above_button.set_text(f"{rows_text(len(above))} with errors above")
        below_button.set_text(f"{rows_text(len(below))} with errors below")
        above_button.visible = bool(above)
        below_button.visible = bool(below)

    # the nearest error row out of view is scrolled to the middle of the grid; the scroll updates the buttons
    def jump_to(index: int) -> None:
        grid.run_grid_method("ensureIndexVisible", index, "middle")

    # a new dataset opens on its first error row, in the middle of the grid as a jump puts it
    async def on_first_data_rendered() -> None:
        buttons_teleport.update()
        if error_indexes:
            jump_to(error_indexes[0])
        await show_out_of_view()

    grid.on("firstDataRendered", on_first_data_rendered)
    grid.on("gridSizeChanged", show_out_of_view)
    grid.on(
        "bodyScroll",
        lambda e: show_out_of_view() if e.args["direction"] == "vertical" else None,
        ["direction"],
        throttle=0.2,
    )
    ui.add_css(GRID_CSS)
    ui.add_body_html(GRID_JS)

    # the grid is updated in place: the columns change with the dataset, so all its options are replaced.
    # edits not submitted are dropped with the dataset they belong to
    async def show_dataset(dataset: str) -> None:
        columns, rows = await run.io_bound(select_cand_as_corr, dataset)
        aud_errors = await run.io_bound(select_aud_errors, dataset)
        edited_rows.clear()
        show_edited_count()
        error_indexes[:] = [index for index, row in enumerate(rows) if is_error_row(aud_errors.get(row["row_id"], []))]
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
