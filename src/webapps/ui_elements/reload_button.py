from collections.abc import Awaitable, Callable

from nicegui import ui

DROPS_EDITS = "Reloading drops the edits not submitted"


# shows the dataset again, on demand. it turns orange when dbt has changed the data under edits not submitted: the page
# keeps those edits, so what it shows is out of date until the reviewer reloads or submits
class ReloadButton(ui.button):
    def __init__(self, on_reload: Callable[[], Awaitable[None]]) -> None:
        super().__init__("Reload", icon="refresh", on_click=on_reload)
        with self:
            self._tooltip = ui.tooltip()
        self.show_current()

    def show_current(self) -> None:
        self.set_background_color("primary")
        self._tooltip.set_text(DROPS_EDITS)

    def show_outdated(self) -> None:
        self.set_background_color("warning")
        self._tooltip.set_text(f"dbt has updated the data. {DROPS_EDITS}")
