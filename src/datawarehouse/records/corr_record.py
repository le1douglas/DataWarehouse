from uuid import UUID

from pydantic import Field

from datawarehouse.records.meta_record import MetaRecord
from datawarehouse.records.record import Record


class CorrRecord(Record):
    """
    Shared base class for every row model of the corrections layer.
    Not meant to be instantiated directly.
    Every subclass declares its own fields, on top of row_id.
    """

    # the key of a correction: the row_id of the bronze row it corrects.
    # it comes from the source and is never generated here, a correction without it is refused
    row_id: UUID  # required key, non-null

    # metadata that is recorded about this row. Not a column of the table: is stored in a separte table.
    # it is left out of model_dump, so a dumped row is still exactly the columns of the source
    meta_records: list[MetaRecord] = Field(default_factory=list, exclude=True)
