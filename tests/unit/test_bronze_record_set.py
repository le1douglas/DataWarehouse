import pytest
from pydantic import ValidationError

from datawarehouse.bronze_record_set import BronzeRecordSet

def test_not_empty_no_row(record_one_field):
    with pytest.raises(ValidationError, match="must contain at least one row"):
        BronzeRecordSet[record_one_field](rows=[])

def test_not_empty_one_row(record_one_field):
    row = record_one_field(
        value="ok",
        meta_extract_date_time="2026-01-01T00:00:00", #unused
        meta_source="test", #unused
    )

    BronzeRecordSet[record_one_field](rows=[row])  # should not raise

