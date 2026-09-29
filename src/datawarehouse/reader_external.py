from pathlib import Path
from typing import Protocol

import pandas as pd


class ExternalReader(Protocol):
    """
    Generic for a class that can read external data i.e.
    Anything that can turn a source string into a DataFrame of raw string fields
    "source" is deliberately generic, 
    could be a file path for CSVReader, or a URL for APIReader.

    #TODO
    Error handling isn't standardized yet: 
    FileNotFoundError for CSV, HTTP errors for an API reader, etc.
    """
    def read(self, source: Path) -> pd.DataFrame: ...