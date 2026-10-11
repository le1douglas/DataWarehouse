# brnz_loader.py
from datetime import datetime
from pathlib import Path

import pandas as pd

from datawarehouse.loader import Loader


class BrnzLoader(Loader):
    """
    The Loader of the bronze layer.

    adds metatada columns like meta_extract_date_time and meta_source.
    """

    @classmethod
    def _add_metadata(cls, df: pd.DataFrame, source: Path) -> pd.DataFrame:
        df["meta_extract_date_time"] = datetime.now()
        df["meta_source"] = str(source)
        return df
