from typing import TypeVar

from pydantic import BaseModel, ConfigDict


class BronzeRecord(BaseModel):
    """
    Shared base class for every row model that belongs in a BronzeRecordSet
    Not meant to be instantiated directly.
    
    """
    model_config = ConfigDict(extra="forbid")


RowT = TypeVar("RowT", bound=BronzeRecord)