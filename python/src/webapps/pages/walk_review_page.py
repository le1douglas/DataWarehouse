"""The review page of a walk, /walk/<walk>/review: its csv as a grid, and its export."""

from datetime import datetime

from nicegui import ui

from webapps.settings import EXPORT_DIR, OLD_EXPORT_DIR, TIMEZONE, WALKS, get_work_in_progress_csv_path
from webapps.state.journal_entry_csv import JournalEntryCsv
from webapps.state.walk import Walk
from webapps.to_old_journal_entries import write_old_journal_entries
from webapps.ui.confirm_dialog import ConfirmDialog
from webapps.ui.review_grid import ReviewGrid
from webapps.ui.status_bar import StatusBar


@ui.page("/walk/{name}/review")
def draw_walk_review_page(name: str) -> None:
    """The csv of the walk of the name as a grid, each value edited in place. Back to the walk page, where
    the pen is connected again, and Export, only once the walk is complete. Another name goes back to the
    home page."""
    if name not in WALKS:
        ui.navigate.to("/")
        return
    journal = JournalEntryCsv(get_work_in_progress_csv_path(name))
    # read once: the grid adds, deletes and moves no row, so the walk stays as complete as it was
    is_complete = Walk(WALKS[name], journal).is_complete()

    async def export() -> None:
        """Copies the csv to EXPORT_DIR, named by today and the walk, <yyyy-mm-dd>-<walk>.csv. Asks first when
        today's export of the walk is there: Cancel keeps it.

        - temporary: the same csv in the old format too, in OLD_EXPORT_DIR under the same name: asks first when
          either is there
        - only once both are written, the csv is emptied for the walk's next pass, and the page goes back to the
          home page, which says it: the grid's rows are gone
        """
        file_name = f"{datetime.now(TIMEZONE):%Y-%m-%d}-{name}.csv"
        target = EXPORT_DIR / file_name
        old_target = OLD_EXPORT_DIR / file_name
        existing = [str(path) for path in (target, old_target) if path.exists()]
        if existing and not await confirm_dialog.ask(f"Overwrite {', '.join(existing)}?", "Overwrite", "save"):
            return
        try:
            journal.export(target)
            write_old_journal_entries(journal.read_rows(), WALKS[name], old_target)
        # ValueError: a row the old format cannot place, as its room, bench or spot is not of the walk
        except (OSError, ValueError) as error:
            ui.notify(f"Not exported: {error}", type="negative")
            return
        journal.empty()
        # the toast on the home page: shown here, it would go with this page
        ui.navigate.to(f"/?exported={target.name}")

    ui.page_title(f"{name.capitalize()} walk: review")
    # the screen's height, so the grid fills what the bar leaves
    ui.query(".nicegui-content").classes("h-screen")
    status_bar = StatusBar()
    with status_bar.left:
        ui.button("Back", icon="arrow_back", on_click=lambda: ui.navigate.to(f"/walk/{name}")).props("flat")
    with status_bar.center:
        ui.label(f"{name.capitalize()} walk: review").classes("text-xl font-bold")
    with status_bar.right:
        export_button = ui.button("Export", icon="file_download", on_click=export).props("flat")
        export_button.set_enabled(is_complete)
    # one dialog for the page: an export that would overwrite one
    confirm_dialog = ConfirmDialog()
    ReviewGrid(journal).classes("w-full grow")
