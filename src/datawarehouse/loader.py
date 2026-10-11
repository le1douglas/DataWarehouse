# loader.py
from pathlib import Path

import pandas as pd
from pydantic import TypeAdapter

from datawarehouse.reader_external import ExternalReader
from datawarehouse.record import RecordT
from datawarehouse.record_set import RecordSet


class Loader:
    """
    Shared base class for every layer's loader.
    Produces a fully validated RecordSet from an ExternalReader, for a given row
    model.
    Takes a reader capable of returnig a dataframe,
    and validates it row wise (against the privided RecordT) and between rows.

    A layer that adds metadata columns overrides _add_metadata, the rest is the same
    for every layer.

    No instances for now, revisit if a looping use case (many files) needs to share state (a reused
    reader instance, aggregated errors across files, etc.) across calls.
    """

    # pass the class type, not a class instance i.e CSVReader not CSVReader()
    @classmethod
    def load(cls, source: Path, reader: type[ExternalReader], record_model: type[RecordT]) -> RecordSet[RecordT]:
        # creates an instance of the reader here
        df = reader().read(source)

        df = cls._add_metadata(df, source)

        # validates each row by making them a RecordT
        rows = TypeAdapter(list[record_model]).validate_python(df.to_dict(orient="records"))

        # validates between rows when creating the RecordSet object
        return RecordSet(rows=rows)


    # adds nothing by default, can be overwritten by subclasses to add metadata columns like meta_extract_date_time and meta_source
    @classmethod
    def _add_metadata(cls, df: pd.DataFrame, source: Path) -> pd.DataFrame:
        return df
