# corrections_loader.py
from pathlib import Path

from pydantic import TypeAdapter

from datawarehouse.record import RecordT
from datawarehouse.record_set import RecordSet
from datawarehouse.reader_external import ExternalReader


class CorrectionsLoader:
    """
    Produces a fully validated RecordSet from an ExternalReader, for a given row
    model.
    Takes a reader capable of returnig a dataframe,
    and validates it row wise (against the privided RecordT) and between rows.

    Unlike BronzeLoader it adds no metadata columns:
    meta_reviewed_by and meta_reviewed_date_time are filled in by the reviewer, in the source.
    """

    #pass the class type, not a class instance i.e ExcelReader not ExcelReader()
    @staticmethod
    def load(source: Path, reader: type[ExternalReader], record_model: type[RecordT]) -> RecordSet[RecordT]:
        #creates an instance of the reader here
        df = reader().read(source)

        #validates each row by making them a RecordT
        rows = TypeAdapter(list[record_model]).validate_python(
            df.to_dict(orient="records")
        )

        #validates between rows when creating the RecordSet object
        return RecordSet(rows=rows)
