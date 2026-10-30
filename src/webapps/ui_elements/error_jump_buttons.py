from nicegui import ui

from webapps.ui_elements.rows_text import rows_text


# over the grid, a button at the top and one at the bottom count the error rows out of view on that side, and jump to
# the nearest one. they are teleported into the grid's .ag-root-wrapper, for the colors of its theme. the grid makes a
# new wrapper with every dataset, so the teleport is updated once the rows are shown. color=None: the default primary
# is a quasar class that is !important, and would cover the red of button_style, which the grid gives
class ErrorJumpButtons(ui.teleport):
    def __init__(self, grid: ui.aggrid, button_style: str) -> None:
        super().__init__(f"#{grid.html_id} .ag-root-wrapper")
        self._grid = grid
        # the indexes of the error rows of the dataset shown, and of those out of view above and below it
        self._error_indexes: list[int] = []
        self._error_above: list[int] = []
        self._error_below: list[int] = []
        with self:
            self._above_button = (
                ui.button(icon="arrow_upward", color=None, on_click=lambda: self._jump_to(self._error_above[-1]))
                .props("rounded")
                .classes("absolute top-14 left-1/2 -translate-x-1/2 z-10")
                .style(button_style)
            )
            self._below_button = (
                ui.button(icon="arrow_downward", color=None, on_click=lambda: self._jump_to(self._error_below[0]))
                .props("rounded")
                .classes("absolute bottom-4 left-1/2 -translate-x-1/2 z-10")
                .style(button_style)
            )
        self._above_button.visible = False
        self._below_button.visible = False
        grid.on("firstDataRendered", self._on_first_data_rendered)
        grid.on("gridSizeChanged", self._show_out_of_view)
        grid.on(
            "bodyScroll",
            lambda e: self._show_out_of_view() if e.args["direction"] == "vertical" else None,
            ["direction"],
            throttle=0.2,
        )

    @property
    def has_errors(self) -> bool:
        return bool(self._error_indexes)

    # the error rows of the dataset about to be shown, as indexes in the order the grid gets the rows
    def set_error_indexes(self, error_indexes: list[int]) -> None:
        self._error_indexes = error_indexes

    # the buttons follow what the grid shows: after a scroll, a resize, or a new dataset
    async def _show_out_of_view(self) -> None:
        pixels = await self._grid.run_grid_method("getVerticalPixelRange")
        sizes = await self._grid.run_grid_method("getSizesForCurrentTheme")
        above, below = _error_rows_out_of_view(self._error_indexes, pixels["top"], pixels["bottom"], sizes["rowHeight"])
        self._error_above = above
        self._error_below = below
        self._above_button.set_text(f"{rows_text(len(above))} with errors above")
        self._below_button.set_text(f"{rows_text(len(below))} with errors below")
        self._above_button.visible = bool(above)
        self._below_button.visible = bool(below)

    # the nearest error row out of view is scrolled to the middle of the grid; the scroll updates the buttons
    def _jump_to(self, index: int) -> None:
        self._grid.run_grid_method("ensureIndexVisible", index, "middle")

    # a new dataset opens on its first error row, in the middle of the grid as a jump puts it
    async def _on_first_data_rendered(self) -> None:
        self.update()
        if self._error_indexes:
            self._jump_to(self._error_indexes[0])
        await self._show_out_of_view()


# the error rows out of view, as indexes in the grid: those above the shown pixels and those below. a row partly in
# view counts as in view. the rows are as high as each other and in the order they were sent: the grid neither sorts
# nor filters
def _error_rows_out_of_view(
    error_indexes: list[int], top: float, bottom: float, row_height: float
) -> tuple[list[int], list[int]]:
    above = [index for index in error_indexes if (index + 1) * row_height <= top]
    below = [index for index in error_indexes if index * row_height >= bottom]
    return above, below
