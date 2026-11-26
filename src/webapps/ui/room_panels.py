"""The open room of the drip and drain page in two panels: another room slides in as the open one slides out."""

from collections.abc import Callable

from nicegui import ui

# the slide by the way the walk moved: forward comes in from the right, back from the left
SLIDES = {True: "slide-left", False: "slide-right"}


class RoomPanels(ui.tab_panels):
    """Two panels, one shown: another room is drawn in the hidden one, which then slides in.

    - draw: draws the open room in the panel it is called in, such as its cards
    - show(index): the index of the open room in the walk. another room slides, the same one is drawn
      again where it is, without a slide, such as after a confirm
    - the slide is set by the move, not by the panels' order: Quasar slides by their order, and with two
      panels taken in turn that is forward and back alternately
    - grow: the height the page leaves, which Quasar passes on to the panel shown. the page must have a
      fixed height, not a minimum one: more than fits scrolls inside the panel
    """

    def __init__(self, draw: Callable[[], None], index: int) -> None:
        super().__init__(value="a", animated=True)
        self.classes("w-full grow")
        self._draw = draw
        self._index = index
        with self:
            # p-2, not Quasar's 16px: room for the ring and the shadow of a card, which the panels clip to slide
            self._panels = {name: ui.tab_panel(name).classes("p-2") for name in ("a", "b")}
        self._draw_in(self.value)

    def show(self, index: int) -> None:
        """Draws the open room: slid in when it is another one."""
        if index == self._index:
            self._draw_in(self.value)
            return
        slide = SLIDES[index > self._index]
        self.props(f"transition-prev={slide} transition-next={slide}")
        hidden = "b" if self.value == "a" else "a"
        self._draw_in(hidden)
        self._index = index
        self.set_value(hidden)

    def _draw_in(self, name: str) -> None:
        panel = self._panels[name]
        panel.clear()
        with panel:
            self._draw()
