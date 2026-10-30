from nicegui import ui


# one box for the errors of the grid cell under the pointer, instead of the grid's tooltips: the grid gives every cell
# its own tooltip, and swapping it from cell to cell flickered. this box stays open from cell to cell, only its text
# and position change. it is drawn by errors_tooltip.vue, and a grid connects to it with grid_handlers
class ErrorsTooltip(ui.element, component="errors_tooltip.vue"):
    # the grid options that show the errors of the hovered cell: a cell without errors shows none.
    # each row carries the descriptions of its errors in "row_errors" and "column_errors", sorted by the grid.
    # getElement is nicegui's: it finds the component of this element in the browser
    def grid_handlers(self) -> dict:
        return {
            ":onCellMouseOver": f"params => getElement({self.id}).show(params)",
            ":onCellMouseOut": f"params => getElement({self.id}).hide()",
        }
