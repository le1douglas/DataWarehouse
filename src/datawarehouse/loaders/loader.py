# loader.py

import pandas as pd
from pydantic import TypeAdapter

from datawarehouse.records.meta_record import MetaRecord
from datawarehouse.records.record import RecordT
from datawarehouse.records.record_set import RecordSet


class Loader:
    """
    Produces one fully validated RecordSet from what a reader returns, for a given row model.
    Validates row wise (against the provided RecordT) and between rows.

    The same for every layer and every reader: the metadata is made by the reader (CSVReader
    stamps the source and the extract date-time, ExcelReader reads what the reviewer filled in)
    and is attached to each row as MetaRecords.

    Static for now, revisit if a looping use case (many files) needs to share state (a reused
    reader instance, aggregated errors across files, etc.) across calls.
    """

    # takes what a reader's read returns, not the reader itself:
    # two dataframes with the same rows in the same order, the data and its metadata
    @staticmethod
    def load(dataframes: tuple[pd.DataFrame, pd.DataFrame], record_model: type[RecordT]) -> RecordSet[RecordT]:
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
