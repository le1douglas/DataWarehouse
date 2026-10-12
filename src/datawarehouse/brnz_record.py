from datetime import datetime
from pathlib import Path

from pydantic import Field

from datawarehouse.meta_record import MetaRecord
from datawarehouse.record import Record


class BrnzRecord(Record):
    """
    Shared base class for every row model of the bronze layer.
    Not meant to be instantiated directly.
    Every subclass declares its own fields, and they are exactly the columns of the source.
    """



    
