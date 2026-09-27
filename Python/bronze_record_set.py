from typing import Generic, TypeVar

from pydantic import BaseModel, model_validator

from bronze_record import BronzeRecordT


class BronzeRecordSet(BaseModel, Generic[BronzeRecordT]):
    """
    A whole batch of row wise validated Bronze rows, treated as one unit.
    Responsable for check across rows for example, checking the whole sei is above a certain size
    Generic over any BronzeRow subtype (e.g. JournalEntryRow)
    """
    rows: list[BronzeRecordT]

    #check that the set is not empty
    @model_validator(mode="after")
    def _not_empty(self) -> "BronzeRecordSet[BronzeRecordT]":
        if len(self.rows) == 0:
            raise ValueError("BronzeRecordSet must contain at least one row")
        return self