import math
from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator



class BronzeRecord(BaseModel):
    """
    Shared base class for every row model that belongs in a BronzeRecordSet
    Not meant to be instantiated directly.
    
    """
    model_config = ConfigDict(extra="forbid")

    
    meta_extract_date_time: datetime                     # required for every record in the bronze layer, non-null
    meta_source:            str = Field(max_length=400)  # required for every record in the bronze layer, non-null

    
    #Transorm empty strings to None across every field, before field-level
    #validation runs. Anything else (including "N/A") passes through untouched.
    #A pandas NaN (float(nan)) reaching here means an ExternalReader failed
    #to convert missing values to None before handing data to this model -
    #that conversion is the reader's responsibility, not this model's, so we
    #raise loudly rather than silently accepting or normalizing it.
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


BronzeRecordT = TypeVar("BronzeRecordT", bound=BronzeRecord)