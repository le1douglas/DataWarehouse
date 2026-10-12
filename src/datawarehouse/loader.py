# loader.py
from datetime import datetime
from pathlib import Path
from typing import Any, overload

from pydantic import TypeAdapter

from datawarehouse.brnz_record import BrnzRecord
from datawarehouse.config import DATASET_JOURNAL_ENTRIES
from datawarehouse.corr_record import CorrRecord
from datawarehouse.meta_record import MetaRecord
from datawarehouse.reader_external import ExternalReader
from datawarehouse.record import RecordT
from datawarehouse.record_set import RecordSet


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

    
    # pass the class type, not a class instance i.e CSVReader not CSVReader()
    @staticmethod
    def load(
        source: Path, reader: type[ExternalReader], record_model: type[RecordT]
    ) -> RecordSet[RecordT]:
        # creates an instance of the reader here
        df = reader().read(source)
        raw_rows = df.to_dict(orient="records")

        # get the metadata
        # bronze records for every row from where and when it was loaded: two MetaRecords per row.
        # the date and time has no time zone, is cut to the second and is the same for every row of the load
        # it is added to the raw row before validation, so a row is created with its metadata already in it
        if issubclass(record_model, BrnzRecord):
            extract_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for raw_row in raw_rows:
                raw_row["meta_records"] = [
                    MetaRecord(
                        kind="source_metadata",
                        description=str(source),
                    ),
                    MetaRecord(
                        kind="extract_date_time",
                        description=extract_date_time,
                    ),
                ]

        # get the actual data
        # validates each row by making them a RecordT
        rows = TypeAdapter(list[record_model]).validate_python(raw_rows)

        # validates between rows when creating the RecordSet object. A RecordSet is never empty.
        record_set = RecordSet[record_model](rows=rows)

        return record_set
