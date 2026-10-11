from pathlib import Path

import pandas as pd

from datawarehouse.record import Record


class CorrRecord(Record):
    """
    Shared base class for every row model of the corrections layer.
    Not meant to be instantiated directly.
    It has no fields: every subclass declares its own, including the meta_ ones.
    """

    # corrections adds nothing:
    # meta_reviewed_by and meta_reviewed_date_time are filled in by the reviewer, in the source.
    # TODO: if we want to add a meta_reviewed_date_time column, we can do it here,
    # but it will be the time of loading, not the time of reviewing.
    @classmethod
    def add_metadata(cls, df: pd.DataFrame, source: Path) -> pd.DataFrame:
        return df
