from typing import Optional

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

    date_time is text with its time zone written, in the format of its
    source (2026-09-17T15:13:08.363212 Europe/Amsterdam): the corrections
    workbook keeps the format, so candidate still sorts it in time order.
    A date_time without a time zone is accepted here too: the castable test
    on candidate reports it.
    """

    date_time: str = Field(max_length=100)  # required, non-null. with a time zone name, see the table's DDL
    subject: str = Field(max_length=50)  # required, non-null
    type: Optional[str] = Field(max_length=50)
    ml: Optional[str] = Field(max_length=50)
    ec: Optional[str] = Field(max_length=50)
    ph: Optional[str] = Field(max_length=50)
    temp: Optional[str] = Field(max_length=50)
    notes: Optional[str] = Field(max_length=400)
    room_raw: Optional[str] = Field(max_length=50)
