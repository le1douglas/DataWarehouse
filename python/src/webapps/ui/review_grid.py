"""The grid of the review page: every row of the walk's csv, each value edited in place."""

from nicegui import events, ui

from webapps.state.journal_entry_csv import CSV_COLUMNS, EDITABLE_COLUMNS, JournalEntryCsv


class ReviewGrid(ui.aggrid):
    """One line per row of the csv, its columns in the csv's order, every value as text.

    - each edit is written to the csv at once, as it is typed: nothing is checked, staging judges it
    - only the EDITABLE_COLUMNS edited, the others greyed out
    - the csv read once, when the page is drawn: a change made to it elsewhere shows on a reload
    """

    def __init__(self, journal: JournalEntryCsv) -> None:
        self._journal = journal
        super().__init__(
            {
                "columnDefs": [_define_column(column) for column in CSV_COLUMNS],
                "rowData": journal.read_rows(),
                # the key of the row, as the csv finds it
                ":getRowId": "params => [params.data.room, params.data.bench, params.data.spot].join('|')",
                "stopEditingWhenCellsLoseFocus": True,
                # the columns stay in the csv's order
                "suppressMovableColumns": True,
            }
        )
        self.on("cellValueChanged", self._write_value)

    def _write_value(self, event: events.GenericEventArguments) -> None:
        """Writes the value edited to its row of the csv. A cell emptied is an empty string."""
        row = event.args["data"]
        value = event.args["newValue"]
        try:
            self._journal.update_value(
                (row["room"], row["bench"], row["spot"]), event.args["colId"], "" if value is None else str(value)
            )
        except (OSError, ValueError) as error:
            ui.notify(f"Not written: {error}", type="negative")


def _define_column(column: str) -> dict:
    """The column of the grid: edited when it is in EDITABLE_COLUMNS, greyed out when not."""
    if column in EDITABLE_COLUMNS:
        return {"field": column, "editable": True}
    return {"field": column, "editable": False, "cellStyle": {"opacity": "0.5"}}
