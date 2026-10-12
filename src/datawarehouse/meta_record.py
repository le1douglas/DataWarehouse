from uuid import UUID

from pydantic import Field

from datawarehouse.record import Record


class MetaRecord(Record):
    """
    One row of a meta table: dev_bronze.meta_bronze or dev_corrections.meta_corrections.
    The same model for both, because every meta table has the same columns.

    One row is one fact about one journal entry: kind says which fact,
    description holds its value as text.

    row_id and kind together are the key, unique in the table. row_id is
    the row_id of the bronze row the fact is about: it is never generated
    here. A row_id that is not in bronze is refused by the database.

    A fact is recorded only when there is something to say, so description
    is required. Empty string is normalized to None and then refused.
    """

    row_id: UUID  # required key, non-null
    dataset: str = Field(max_length=50)  # required, non-null
    kind: str = Field(max_length=50)  # required key, non-null
    description: str = Field(max_length=400)  # required, non-null
