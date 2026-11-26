"""The status bar of the drip and drain page: a bar at the top, its elements given by the page."""

from nicegui import ui


class StatusBar(ui.grid):
    """Where its elements sit, nothing of what they are: the page draws them in left, center and right.

    - center: in the middle of the bar, whatever is at the sides
    - three columns: the outer two share what is left of the width
    """

    def __init__(self) -> None:
        super().__init__(columns="1fr auto 1fr")
        self.classes("w-full items-center")
        with self:
            self.left = ui.row().classes("justify-self-start items-center")
            self.center = ui.row().classes("justify-self-center items-center")
            self.right = ui.row().classes("justify-self-end items-center")
