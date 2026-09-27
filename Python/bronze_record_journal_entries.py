from datetime import datetime
from typing import Optional

from pydantic import Field, model_validator

from bronze_record import BronzeRecord



class BronzeRecordJournalEntries(BronzeRecord):
    """
    One row of Bronze.journal_entries.

    Bronze does no type conversion on source data — every source field
    stays a string, matching NVARCHAR in SQL Server, even where the
    content is numeric.

    Empty string ("") means "nothing recorded" and is normalized to
    None. A literal "N/A" (or similar) is NOT normalized. It's the
    data collector explicitly marking the field as not applicable, and
    that intent is preserved as-is, not conflated with a missing value.

    meta_extract_date_time is a plain datetime, matching SQL Server's
    datetime2 (no timezone concept). By convention this value represents
    Amsterdam local time. That's the caller's responsibility entirely;
    this model does not verify tzinfo one way or the other.
    """

    date_time: str = Field(max_length=50)              # required, non-null
    subject:   Optional[str] = Field(max_length=50)      # required key, nullable
    notes:     Optional[str] = Field(max_length=400)
    type:      Optional[str] = Field(max_length=50)
    ec:        str = Field(max_length=50)               # required, non-null
    ec_pore:   Optional[str] = Field(max_length=50)
    ec_bulk:   Optional[str] = Field(max_length=50)
    ph:        str = Field(max_length=50)               # required, non-null
    mc:        Optional[str] = Field(max_length=50)
    temp:      Optional[str] = Field(max_length=50)
    device:    Optional[str] = Field(max_length=50)
    media:     Optional[str] = Field(max_length=50)
    tags:      Optional[str] = Field(max_length=50)

    meta_extract_date_time: datetime                     # required, non-null
    meta_source:            str = Field(max_length=400)  # required, non-null


    #Transorm empty strings to None across every field, before field-level
    #validation runs. Anything else (including "N/A") passes through untouched
    @model_validator(mode="before")
    @classmethod
    def _empty_string_to_null(cls, data: dict) -> dict:
        if isinstance(data, dict):
            return {k: (None if v == "" else v) for k, v in data.items()}
        return data