from collections.abc import Awaitable, Callable

from nicegui import ui

from webapps.ui_elements.rows_text import rows_text


# the submit of a reviewer's edits: the button holds the rows edited since the dataset was shown or last submitted, and
# gives them to on_submit. it counts the edited rows, so a reviewer sees there is something to submit: Submit (1 row).
# it is disabled when there is nothing to submit, or while on_submit runs: an edit made then does not enable it
class SubmitButton(ui.button):
    def __init__(self, on_submit: Callable[[list[dict]], Awaitable[None]]) -> None:
        super().__init__("Submit", on_click=self._submit)
        self._on_submit = on_submit
        # by row_id: a row edited twice is kept once, as it is now
        self._edited_rows: dict[str, dict] = {}
        # on_submit is running
        self._submit_running = False
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
        self.set_enabled(count > 0 and not self._submit_running)
        if count == 0:
            self.set_text("Submit")
        else:
            self.set_text(f"Submit ({rows_text(count)})")

    # there is no second submit while on_submit runs
    async def _submit(self) -> None:
        self._submit_running = True
        self._show_edited_count()
        try:
            await self._on_submit(list(self._edited_rows.values()))
        finally:
            self._submit_running = False
            self._show_edited_count()
