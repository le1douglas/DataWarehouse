# brnz_loader.py
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter

from datawarehouse.reader_external import ExternalReader
from datawarehouse.record import RecordT
from datawarehouse.record_set import RecordSet


class BrnzLoader:
    """
    Produces a fully validated RecordSet from an ExternalReader, for a given row
    model.
    Takes a reader capable of returnig a dataframe,
    and validates it row wise (against the privided RecordT) and between rows.

    adds metatada columns like meta_extract_date_time and meta_source.

    Static for now, revisit if a looping use case (many files) needs to share state (a reused
    reader instance, aggregated errors across files, etc.) across calls.
    """

    # pass the class type, not a class instance i.e CSVReader not CSVReader()
    @staticmethod
    def load(source: Path, reader: type[ExternalReader], record_model: type[RecordT]) -> RecordSet[RecordT]:
        # creates an instance of the reader here
        df = reader().read(source)
        print(df)

        df["meta_extract_date_time"] = datetime.now()
        df["meta_source"] = str(source)

        # validates each row by making them a RecordT
        rows = TypeAdapter(list[record_model]).validate_python(df.to_dict(orient="records"))

        # validates between rows when creating the RecordSet object
        return RecordSet(rows=rows)
