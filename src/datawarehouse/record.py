import math
from pathlib import Path
from typing import TypeVar

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator, Field

from datawarehouse.meta_record import MetaRecord


class Record(BaseModel):
    """
    Shared base class for every row model that belongs in a RecordSet
    Not meant to be instantiated directly.
    It has no fields: every subclass declares its own, including the meta_ ones.

    """

    model_config = ConfigDict(extra="forbid")

    # Transorm empty strings to None across every field, before field-level
    # validation runs. Anything else (including "N/A") passes through untouched.
    # A pandas NaN (float(nan)) reaching here means an ExternalReader failed
    # to convert missing values to None before handing data to this model -
    # that conversion is the reader's responsibility, not this model's, so we
    # raise loudly rather than silently accepting or normalizing it.
    @model_validator(mode="before")
    @classmethod
    def _empty_string_to_null(cls, data: dict) -> dict:
        for k, v in data.items():
            if isinstance(v, float) and math.isnan(v):
                raise ValueError(
                    f'Field "{k}" received a pandas NaN value directly - '
                    f"this indicates an ExternalReader did not convert "
                    f"missing values to None before this model saw them."
                )
        return {k: (None if v == "" else v) for k, v in data.items()}

    
    # metadata that is recorded about this row. Not a column of the table: is stored in a seperte table.
    # it is left out of model_dump, so a dumped row is still exactly the columns of the source
    meta_records: list[MetaRecord] = Field(default_factory=list, exclude=True)


RecordT = TypeVar("RecordT", bound=Record)
