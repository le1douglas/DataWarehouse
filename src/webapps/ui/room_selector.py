"""The room selector of the drip and drain page: the room shown, and buttons to the previous and the next."""

from collections.abc import Awaitable, Callable

from nicegui import ui


class RoomSelector(ui.row):
    """Previous and Next through rooms, which stop at the first and the last room.

    It does not change the room itself: a button asks for the neighbour with on_select, and the page
    shows it with set_room once it has moved there, so the page may refuse, such as when a typed entry
    would be lost.
    """

    def __init__(self, rooms: tuple[str, ...], room: str, on_select: Callable[[str], Awaitable[None]]) -> None:
        super().__init__()
        self.rooms = rooms
        self.room = room
        self._on_select = on_select
        self.classes("items-center no-wrap")
        with self:
            previous = ui.button("Prev", icon="chevron_left", on_click=self._select_previous).props("flat")
            previous.bind_enabled_from(self, "room", backward=lambda room: room != self.rooms[0])
            label = ui.label().classes("text-xl font-bold")
            label.bind_text_from(self, "room")
            next_ = ui.button("Next", icon="chevron_right", on_click=self._select_next).props("flat icon-right")
            next_.bind_enabled_from(self, "room", backward=lambda room: room != self.rooms[-1])

    def set_room(self, room: str) -> None:
        """Shows the room the page has moved to."""
        self.room = room

    async def _select_previous(self) -> None:
        await self._select_neighbour(-1)

    async def _select_next(self) -> None:
        await self._select_neighbour(1)

    async def _select_neighbour(self, step: int) -> None:
        index = self.rooms.index(self.room) + step
        if 0 <= index < len(self.rooms):
            # async: the page may ask first
            await self._on_select(self.rooms[index])
