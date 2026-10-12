from pathlib import Path

import pandas as pd

from datawarehouse.record import Record


class CorrRecord(Record):
    """
    Shared base class for every row model of the corrections layer.
    Not meant to be instantiated directly.
    It has no fields: every subclass declares its own.

    Corrections metadata is not a column of the row: it goes to the meta table of the layer.
    Who reviewed a correction and when is decided by the reviewer, so the upload hands the
    metadata over as a table of its own, already one MetaRecord per row.
    """

    # corrections adds nothing to the rows: its metadata is a second table of the upload
    @classmethod
    def add_metadata(cls, df: pd.DataFrame, source: Path) -> pd.DataFrame:
        return df
