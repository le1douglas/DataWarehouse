from datetime import datetime
from pathlib import Path

import pandas as pd

from datawarehouse.record import Record


class BrnzRecord(Record):
    """
    Shared base class for every row model of the bronze layer.
    Not meant to be instantiated directly.
    It has no fields: every subclass declares its own, including the meta_ ones.
    """

    # bronze stamps every row with when and from where it was loaded
    @classmethod
    def add_metadata(cls, df: pd.DataFrame, source: Path) -> pd.DataFrame:
        df["meta_extract_date_time"] = datetime.now()
        df["meta_source"] = str(source)
        return df
