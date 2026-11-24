"""The four spots of a room, taken one after the other, as the csv says: no UI, so it is tested without a browser."""

from webapps.state.journal_csv import JournalCsv, csv_spot
from webapps.state.quadrant_draft import QuadrantDraft

# the spots of a room in the order they are taken, as LINE_NAMES in bluelab_datastreamer/drip_drain.py
SPOTS = ("Drip Left", "Drip Right", "Drain Left", "Drain Right")


class Room:
    """The csv as last read, the spot being taken, and its draft.

    The csv (journal_csv.py) is the only record of what is confirmed: a spot with a row is confirmed,
    and the current spot is the first without one in the order of SPOTS. Confirm appends the row of the
    current spot, delete removes a row, and after each the csv is read again. A deleted spot is one
    without a row again, so it is taken again before going on.

    The current spot has a draft (quadrant_draft.py), the only thing not in the csv: the live values
    of the pen and the ml and remarks typed. A new one whenever the current spot changes.
    """

    def __init__(self, journal: JournalCsv) -> None:
        self.journal = journal
        # the rows by spot as the csv writes it
        self.rows: dict[str, dict] = {}
        # the draft of the current spot, None when every spot has its row
        self.draft: QuadrantDraft | None = None
        self.read()

    @property
    def current_spot(self) -> str | None:
        """The spot being taken, None when every spot has its row."""
        return self.draft.spot if self.draft is not None else None

    @property
    def ready(self) -> bool:
        """The draft has what its row needs."""
        return self.draft is not None and self.draft.ready

    def row(self, spot: str) -> dict | None:
        """The row of the spot in the csv, None while it has none."""
        return self.rows.get(csv_spot(spot))

    def draft_of(self, spot: str) -> QuadrantDraft | None:
        """The draft, when the spot is the current one."""
        return self.draft if spot == self.current_spot else None

    def set_live(self, quantity: str, value: float | None) -> None:
        """A live value of the pen, for the current spot. Ignored when every spot has its row."""
        if self.draft is not None:
            self.draft.set_live(quantity, value)

    def forget_live(self) -> None:
        """Forgets the live values of the current spot, such as when the pen is gone."""
        if self.draft is not None:
            self.draft.forget_live()

    def read(self) -> None:
        """Reads the csv again, and starts a draft when the current spot changes: after a confirm, or a delete
        before it."""
        self.rows = self.journal.rows()
        current = next((spot for spot in SPOTS if self.row(spot) is None), None)
        if current is None:
            self.draft = None
        elif self.draft is None or self.draft.spot != current:
            self.draft = QuadrantDraft(current)

    def confirm(self, device: str) -> None:
        """Appends the row of the draft, taken now by the device. A PermissionError while the csv is open in
        another program."""
        if not self.ready:
            raise ValueError("the draft is not ready to be confirmed")
        draft = self.draft
        self.journal.append(draft.spot, draft.values, draft.ml, draft.remarks, device)
        self.read()

    def delete(self, spot: str) -> None:
        """Removes the row of the spot. A PermissionError while the csv is open in another program."""
        self.journal.delete(spot)
        self.read()
