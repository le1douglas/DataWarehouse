# loader.py
from datetime import datetime
from pathlib import Path
from typing import Any, overload

import pandas as pd
from pydantic import TypeAdapter

from datawarehouse.config import DATASET_JOURNAL_ENTRIES
from datawarehouse.readers.reader_external import ExternalReader
from datawarehouse.records.brnz_record import BrnzRecord
from datawarehouse.records.corr_record import CorrRecord
from datawarehouse.records.meta_record import MetaRecord
from datawarehouse.records.record import RecordT
from datawarehouse.records.record_set import RecordSet


class Loader:
    """
    Produces two fully validated RecordSets from an ExternalReader: the rows, for a given row
    model, and their metadata, always as MetaRecord.
    Takes a reader capable of returnig a dataframe,
    and validates it row wise (against the privided RecordT) and between rows.

    The same for every layer. What differs per layer is the metadata that is created at load
    time, and that is decided by the row model's layer: only bronze has any.

    Static for now, revisit if a looping use case (many files) needs to share state (a reused
    reader instance, aggregated errors across files, etc.) across calls.
    """

    
    # takes what ExcelReader.read returns, not the reader itself:
    # two dataframes with the same rows in the same order, the data and its metadata
    @staticmethod
    def load_excel(
        dataframes: tuple[pd.DataFrame, pd.DataFrame], record_model: type[RecordT]
    ) -> RecordSet[RecordT]:
        data_df, meta_df = dataframes
        raw_rows = data_df.to_dict(orient="records")
        raw_meta_rows = meta_df.to_dict(orient="records")

        # get the metadata
        # one MetaRecord per metadata column: the column name is the kind, the cell is the description.
        # an empty cell stays None, so MetaRecord refuses it instead of storing the text "None"
        # it is added to the raw row before validation, so a row is created with its metadata already in it
        for raw_row, raw_meta_row in zip(raw_rows, raw_meta_rows, strict=True):
            raw_row["meta_records"] = [
                MetaRecord(
                    kind=kind,
                    description=str(description),
                )
                for kind, description in raw_meta_row.items()
            ]

        # get the actual data
        # validates each row by making them a RecordT
        rows = TypeAdapter(list[record_model]).validate_python(raw_rows)

        # validates between rows when creating the RecordSet object. A RecordSet is never empty.
        record_set = RecordSet[record_model](rows=rows)

        return record_set
