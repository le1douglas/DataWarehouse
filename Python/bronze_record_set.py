from typing import Generic, TypeVar

from pydantic import BaseModel, model_validator

from bronze_record import RowT


class BronzeRecordSet(BaseModel, Generic[RowT]):
    """
    A whole batch of row wise validated Bronze rows, treated as one unit.
    Responsable for check across rows for example, checking the whole sei is above a certain size
    Generic over any BronzeRow subtype (e.g. JournalEntryRow)
    """
    rows: list[RowT]

    #check that the set is not empty
    @model_validator(mode="after")
    def _not_empty(self) -> "BronzeRecordSet[RowT]":
        if len(self.rows) == 0:
            raise ValueError("BronzeRecordSet must contain at least one row")
        return self