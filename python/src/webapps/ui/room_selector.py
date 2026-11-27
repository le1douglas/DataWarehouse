"""The room selector of the drip and drain page: the room shown, and buttons to the previous and the next."""

from collections.abc import Callable
from typing import Any

from nicegui import ui


class RoomSelector(ui.row):
    """Prev and Next through the rooms, the room shown between them.

    It knows nothing of the walk's rooms: the walk decides.
    - a button asks for a move with on_move: -1 the previous room, 1 the next
    - has_room says whether there is a room that way: the button disabled when not
    - set_room shows the room the walk has moved to, by a button, a key, or a confirm that completes a room
    """

    def __init__(self, room: str, has_room: Callable[[int], bool], on_move: Callable[[int], Any]) -> None:
        super().__init__()
        self.room = room
        self.classes("items-center no-wrap")
        with self:
            previous = ui.button("Prev", icon="chevron_left", on_click=lambda: on_move(-1)).props("flat")
            # asked again whenever the room changes
            previous.bind_enabled_from(self, "room", backward=lambda _: has_room(-1))
            label = ui.label().classes("text-xl font-bold")
            label.bind_text_from(self, "room")
            next_ = ui.button("Next", icon="chevron_right", on_click=lambda: on_move(1)).props("flat icon-right")
            next_.bind_enabled_from(self, "room", backward=lambda _: has_room(1))

    def set_room(self, room: str) -> None:
        """Shows the room the walk has moved to."""
        self.room = room
