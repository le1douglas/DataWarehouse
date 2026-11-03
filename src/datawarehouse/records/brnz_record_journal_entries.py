from typing import Optional

from datawarehouse.records.brnz_record import BrnzRecord


class BrnzRecordJournalEntries(BrnzRecord):
    """
    One row of dw_bronze.brnz_journal_entries.

    A shape check only: every column of the source must be there, and
    every value stays a string, matching TEXT in PostgreSQL, even where
    the content is numeric. The rules on the values are dbt data tests.

    The key, row_id, is not a field: the database assigns it on insert.

    Empty string ("") means "nothing recorded" and is normalized to
    None. A literal "N/A" (or similar) is NOT normalized.
    """

    date_time: Optional[str]
    device: Optional[str]
    spot: Optional[str]
    ml: Optional[str]
    ec: Optional[str]
    ph: Optional[str]
    temperature: Optional[str]
    room: Optional[str]
