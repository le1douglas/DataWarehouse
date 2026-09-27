from pathlib import Path
from typing import Protocol

import pandas as pd


class DataFrameReader(Protocol):
    """
    Anything that can turn a source Path into a DataFrame of raw
    string fields. CSVReader satisfies this as-is. A future APIReader
    would take a Path too (e.g. representing a cached/local copy) or
    this protocol gets revisited if a URL-based reader needs something
    that isn't Path-shaped at all.

    Error handling isn't standardized yet: each concrete reader raises
    whatever's natural for its source (FileNotFoundError for CSV, etc.)
    — deferred for later.
    """
    def read(self, source: Path) -> pd.DataFrame: ...