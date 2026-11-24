"""The pen selector of the drip and drain page: one button, Connect or Disconnect, and the status of the pen."""

from nicegui import ui

from webapps.pens.one_pen import OnePen

# the button by whether the pen is connected: its text, icon and colour
TOGGLE_LOOKS = {
    False: ("Connect pen", "bluetooth", "primary"),
    True: ("Disconnect", "bluetooth_disabled", "grey"),
}


class PenSelector(ui.row):
    """The button and the status of the pen, read from the pen itself: it keeps no copy of either.

    The pen makes the button connect or disconnect it (attach), as Chrome opens its chooser only from a
    click in the browser.
    """

    def __init__(self, pen: OnePen) -> None:
        super().__init__()
        self.classes("w-full items-center")
        with self:
            toggle = ui.button()
            toggle.bind_text_from(pen, "connected", backward=lambda connected: TOGGLE_LOOKS[connected][0])
            toggle.bind_icon_from(pen, "connected", backward=lambda connected: TOGGLE_LOOKS[connected][1])
            toggle.bind_background_color_from(pen, "connected", backward=lambda connected: TOGGLE_LOOKS[connected][2])
            label = ui.label()
            label.bind_text_from(pen, "connected", backward=lambda connected: format_pen_status(pen.name, connected))
        pen.attach(toggle)


def format_pen_status(name: str, connected: bool) -> str:
    """The status of the pen, next to its button."""
    if not connected:
        return "not connected"
    return f"{name or 'pen without a name'} connected"
