from collections.abc import Awaitable, Callable

from nicegui import run, ui

from webapps.orchestration import run_dbt_build
from webapps.queries import upsert_corrections
from webapps.ui_elements.rows_text import rows_text

# a placeholder until the app knows who is logged in
REVIEWER = "Claude"


# the submit of a reviewer's edits: the button holds the rows edited since the dataset was shown or last submitted,
# writes them to corrections, and runs dbt build. it counts the edited rows, so a reviewer sees there is something to
# submit: Submit (1 row). it is disabled when there is nothing to submit, or while a build runs: an edit made then does
# not enable it.
# get_dataset gives the dataset shown, on_saved shows a dataset again, has_errors tells if the dataset shown has errors
class SubmitButton(ui.button):
    def __init__(
        self,
        get_dataset: Callable[[], str],
        on_saved: Callable[[str], Awaitable[None]],
        has_errors: Callable[[], bool],
    ) -> None:
        super().__init__("Submit", on_click=self._submit)
        self._get_dataset = get_dataset
        self._on_saved = on_saved
        self._has_errors = has_errors
        # by row_id: a row edited twice is kept once, as it is now
        self._edited_rows: dict[str, dict] = {}
        # a dbt build started by this button is running
        self._build_running = False
        self._show_edited_count()

    @property
    def has_edits(self) -> bool:
        return bool(self._edited_rows)

    def add_edit(self, row: dict) -> None:
        self._edited_rows[row["row_id"]] = row
        self._show_edited_count()

    # edits not submitted are dropped with the dataset they belong to
    def clear_edits(self) -> None:
        self._edited_rows.clear()
        self._show_edited_count()

    def _show_edited_count(self) -> None:
        count = len(self._edited_rows)
        self.set_enabled(count > 0 and not self._build_running)
        if count == 0:
            self.set_text("Submit")
        else:
            self.set_text(f"Submit ({rows_text(count)})")

    # the dataset is shown again after a submit: the grid shows candidate as it is now, with the corrections, and no
    # cell is edited any more. then dbt build takes the corrections through to audit and silver; while it runs there
    # is no second submit, and when it ends the page's on_run_end shows the dataset again
    async def _submit(self) -> None:
        dataset = self._get_dataset()
        submitted = rows_text(len(self._edited_rows))
        await run.io_bound(upsert_corrections, dataset, list(self._edited_rows.values()), REVIEWER)
        await self._on_saved(dataset)
        self._build_running = True
        self._show_edited_count()
        building = ui.notification(f"Submitted {submitted}: dbt build is running", spinner=True, timeout=None)
        try:
            passed = await run_dbt_build()
        finally:
            building.dismiss()
            self._build_running = False
            self._show_edited_count()
        # rows with errors are told by on_run_end. without any, the failure is elsewhere: dbt could not run, and then
        # no end is announced, or another dataset failed
        if not passed and not self._has_errors():
            ui.notify("dbt build did not pass: see the webapps log", type="warning")
