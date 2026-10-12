from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from datawarehouse.corr_record import CorrRecord


class CorrRecordJournalEntries(CorrRecord):
    """
    One row of dev_corrections.corr_journal_entries.

    row_id is the key, unique in the table. It is the row_id of the bronze
    row being corrected: it comes from the upload and is never generated
    here. A row_id that is not in bronze is refused by the database.

    date_time is a plain datetime cut to the second, matching PostgreSQL's
    TIMESTAMP(0) (no timezone concept).

    Unlike bronze, corrections are typed: the measurements are numbers,
    matching NUMERIC in PostgreSQL. A correction that is not a number is
    rejected here, before it reaches the database.

    The row has no metadata: who reviewed it and when is written to
    dev_corrections.meta_corrections, as rows of their own in the upload.
    """

    row_id: UUID  # required key, non-null
    date_time: datetime  # required, non-null
    subject: str = Field(max_length=50)  # required, non-null
    type: Optional[str] = Field(max_length=50)
    ml: Optional[Decimal]
    ec: Optional[Decimal]
    ph: Optional[Decimal]
    temp: Optional[Decimal]
    notes: Optional[str] = Field(max_length=400)
    room: Optional[str] = Field(max_length=50)
