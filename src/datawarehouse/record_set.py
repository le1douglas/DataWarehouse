from typing import Generic

from pydantic import BaseModel, model_validator

from datawarehouse.record import RecordT


class RecordSet(BaseModel, Generic[RecordT]):
    """
    A whole batch of row wise validated rows, treated as one unit.
    Responsable for check across rows for example, checking the whole sei is above a certain size
    Generic over any Record subtype (e.g. BrnzRecordJournalEntries)
    """

    rows: list[RecordT]

    # check that the set is not empty
    @model_validator(mode="after")
    def _not_empty(self) -> "RecordSet[RecordT]":
        if len(self.rows) == 0:
            raise ValueError("RecordSet must contain at least one row")
        return self
