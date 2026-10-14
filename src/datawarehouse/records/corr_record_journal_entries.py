from datetime import datetime
from typing import Optional

from pydantic import Field

from datawarehouse.records.corr_record import CorrRecord


class CorrRecordJournalEntries(CorrRecord):
    """
    One row of dev_corrections.corr_journal_entries.

    row_id is the key, unique in the table. It is declared in CorrRecord.
    date_time is a plain datetime cut to the second, matching PostgreSQL's
    TIMESTAMP(0) (no timezone concept).

    The measurements are text, like in staging, matching VARCHAR in
    PostgreSQL. A correction that is not a number is accepted here: the
    castable test on candidate reports it, and silver is not built until
    it is corrected again.
    """

    date_time: datetime  # required, non-null
    subject: str = Field(max_length=50)  # required, non-null
    type: Optional[str] = Field(max_length=50)
    ml: Optional[str] = Field(max_length=50)
    ec: Optional[str] = Field(max_length=50)
    ph: Optional[str] = Field(max_length=50)
    temp: Optional[str] = Field(max_length=50)
    notes: Optional[str] = Field(max_length=400)
    room: Optional[str] = Field(max_length=50)
