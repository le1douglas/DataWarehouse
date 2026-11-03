# loader.py

import pandas as pd
from pydantic import TypeAdapter

from datawarehouse.records.record import RecordT
from datawarehouse.records.record_set import RecordSet


class UploadRefused(Exception):
    """A file that is not accepted, with the message for the user."""


class Loader:
    """
    Produces one fully validated RecordSet from what a reader returns, for a given row model.
    Validates row wise (against the provided RecordT) and between rows.

    Static for now, revisit if a looping use case (many files) needs to share state (a reused
    reader instance, aggregated errors across files, etc.) across calls.
    """

    # takes what a reader's read returns, not the reader itself
    @staticmethod
    def load(data_df: pd.DataFrame, record_model: type[RecordT]) -> RecordSet[RecordT]:
        columns = list(record_model.model_fields)

        # a required column that is missing refuses the file, an extra one does not
        missing = [column for column in columns if column not in data_df.columns]
        if missing:
            raise UploadRefused(f"Upload refused: required column missing: {', '.join(missing)}.")

        extra = [column for column in data_df.columns if column not in columns]
        if extra:
            print(f"Ignored extra columns: {', '.join(extra)}")

        raw_rows = data_df[columns].to_dict(orient="records")

        # validates each row by making them a RecordT
        rows = TypeAdapter(list[record_model]).validate_python(raw_rows)

        # validates between rows when creating the RecordSet object. A RecordSet is never empty.
        record_set = RecordSet[record_model](rows=rows)

        return record_set
