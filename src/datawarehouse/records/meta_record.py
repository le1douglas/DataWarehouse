from pydantic import Field

from datawarehouse.records.record import Record


class MetaRecord(Record):
    """
    One row of a meta table: every meta table has the same columns regardless of the schema.

    One row is one fact about one journal entry: kind says which fact,
    description holds its value as text. Every kind starts with meta_.

    row_id is not a field here: the database adds the row_id of the row
    the metadata belongs to.

    A fact is recorded only when there is something to say, so description
    is required. Empty string is normalized to None and then refused.
    """

    kind: str = Field(max_length=50)  # required key, non-null
    description: str = Field(max_length=400)  # required, non-null
