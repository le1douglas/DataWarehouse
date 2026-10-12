from pydantic import Field

from datawarehouse.record import Record


class MetaRecord(Record):
    """
    One row of a meta table: every meta table has the same columns regardless of the schema.

    One row is one fact about one entity: kind says which fact,
    description holds its value as text.

    row_id and dataset are keys in the database and not fields here
    

    A fact is recorded only when there is something to say, so description
    is required. Empty string is normalized to None and then refused.
    """

    kind: str = Field(max_length=50)  # required key, non-null
    description: str = Field(max_length=400)  # required, non-null
