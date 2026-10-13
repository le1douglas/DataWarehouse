from datetime import datetime
from pathlib import Path

from pydantic import Field

from datawarehouse.records.meta_record import MetaRecord
from datawarehouse.records.record import Record


class BrnzRecord(Record):
    """
    Shared base class for every row model of the bronze layer.
    Not meant to be instantiated directly.
    Every subclass declares its own fields, and they are exactly the columns of the source.
    """

    # metadata that is recorded about this row. Not a column of the table: is stored in a separte table.
    # it is left out of model_dump, so a dumped row is still exactly the columns of the source
    meta_records: list[MetaRecord] = Field(default_factory=list, exclude=True)

    
