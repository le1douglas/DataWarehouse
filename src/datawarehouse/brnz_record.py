from datetime import datetime
from pathlib import Path

import pandas as pd

from datawarehouse.record import Record


class BrnzRecord(Record):
    """
    Shared base class for every row model of the bronze layer.
    Not meant to be instantiated directly.
    It has no fields: every subclass declares its own, and they are exactly the columns of the source.

    Bronze metadata is not a column of the row: it goes to the meta table of the layer,
    as one MetaRecord per kind for every row loaded.
    """

    # bronze adds nothing to the rows: its metadata is written to the meta table, see load_metadata
    @classmethod
    def add_metadata(cls, df: pd.DataFrame, source: Path) -> pd.DataFrame:
        return df

    # bronze records for every row when and from where it was loaded, as kind -> description.
    # the date and time has no time zone and is cut to the second
    @classmethod
    def load_metadata(cls, source: Path) -> dict[str, str]:
        return {
            "extract_date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": str(source),
        }
