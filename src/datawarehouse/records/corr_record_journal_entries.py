from typing import ClassVar, Optional

from pydantic import Field

from datawarehouse.records.corr_record import CorrRecord


class CorrRecordJournalEntries(CorrRecord):
    """
    One row of dw_corrections.corr_journal_entries.

    row_id is the key, unique in the table. It is declared in CorrRecord.
    Every column except row_id is text, like in staging, matching VARCHAR
    in PostgreSQL. A correction that cannot be cast (a date_time that is
    not a timestamp, a measurement that is not a number) is accepted here:
    the castable test on candidate reports it, and silver is not built
    until it is corrected again.

    date_time must have the shape YYYY-MM-DD HH:MM:SS, like the check
    constraint on the table: candidate sorts room groups by its text, so a
    value in another shape is refused even when it is a valid timestamp.
    """

    # the shape of date_time in staging and corrections, the same as the check constraint of the table
    DATE_TIME_SHAPE: ClassVar[str] = r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$"

    date_time: str = Field(max_length=50, pattern=DATE_TIME_SHAPE)  # required, non-null
    subject: str = Field(max_length=50)  # required, non-null
    type: Optional[str] = Field(max_length=50)
    ml: Optional[str] = Field(max_length=50)
    ec: Optional[str] = Field(max_length=50)
    ph: Optional[str] = Field(max_length=50)
    temp: Optional[str] = Field(max_length=50)
    notes: Optional[str] = Field(max_length=400)
    room_raw: Optional[str] = Field(max_length=50)
