"""The one yes or no dialog of the drip and drain page, its question set by the page each time it asks."""

from nicegui import ui


class ConfirmDialog(ui.dialog):
    """Cancel, or the answer that loses something, such as Delete or Discard.

    - Enter answers, as the focus starts on the answer. Escape or a click outside cancels
    - one for the page, asked again with another question each time
    """

    def __init__(self) -> None:
        super().__init__()
        with self, ui.card():
            self._question = ui.label()
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=self.close).props("flat")
                self._answer = ui.button(color="negative", on_click=lambda: self.submit(True)).props("autofocus")

    async def ask(self, question: str, answer: str, icon: str) -> bool:
        """Opens with the question and the answer's text and icon. True only when the answer is clicked."""
        self._question.set_text(question)
        self._answer.set_text(answer)
        self._answer.props(f"icon={icon}")
        return await self is True
