from typing import Optional

from pydantic import Field

from datawarehouse.records.brnz_record import BrnzRecord


class BrnzRecordJournalEntries(BrnzRecord):
    """
    One row of dev_bronze.brnz_journal_entries.

    Bronze does no type conversion on source data — every source field
    stays a string, matching VARCHAR in PostgreSQL, even where the
    content is numeric.

    The key, row_id, is not a field: the database assigns it on insert.

    Empty string ("") means "nothing recorded" and is normalized to
    None. A literal "N/A" (or similar) is NOT normalized. It's the
    data collector explicitly marking the field as not applicable, and
    that intent is preserved as-is, not conflated with a missing value.
    """

    date_time: str = Field(max_length=50)
    subject: str = Field(max_length=50)
    notes: Optional[str] = Field(max_length=400)
    type: Optional[str] = Field(max_length=50)
    ec: str = Field(max_length=50)  # required, non-null
    ec_pore: Optional[str] = Field(max_length=50)
    ec_bulk: Optional[str] = Field(max_length=50)
    ph: str = Field(max_length=50)  # required, non-null
    mc: Optional[str] = Field(max_length=50)
    temp: Optional[str] = Field(max_length=50)
    device: Optional[str] = Field(max_length=50)
    media: Optional[str] = Field(max_length=50)
    tags: Optional[str] = Field(max_length=50)
