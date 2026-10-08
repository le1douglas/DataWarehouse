from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from datawarehouse.record import Record


class CorrRecordJournalEntries(Record):
    """
    One row of dev_corrections.corr_journal_entries.

    date_time and subject together are the key, unique in the table.
    date_time is a plain datetime cut to the second, matching PostgreSQL's
    TIMESTAMP(0) (no timezone concept).

    Unlike bronze, corrections are typed: the measurements are numbers,
    matching NUMERIC in PostgreSQL. A correction that is not a number is
    rejected here, before it reaches the database.
    """

    date_time: datetime  # required key, non-null
    subject: str = Field(max_length=50)  # required key, non-null
    type: Optional[str] = Field(max_length=50)
    ml: Optional[Decimal]
    ec: Optional[Decimal]
    ph: Optional[Decimal]
    temp: Optional[Decimal]
    notes: Optional[str] = Field(max_length=400)
    room: Optional[str] = Field(max_length=50)

    meta_reviewed_by: str = Field(max_length=50)  # required, non-null
    meta_reviewed_date_time: datetime  # required, non-null
