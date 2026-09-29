# tests/test_bronze_loader.py
from pathlib import Path

import pytest
from pydantic import ValidationError

from datawarehouse.bronze_loader import BronzeLoader
from datawarehouse.bronze_record_set import BronzeRecordSet


from datetime import datetime

def test_load_valid(reader_valid_one_row, record_one_field):
    source = Path("some/path/to/file.csv")
    before = datetime.now()

    result = BronzeLoader.load(source, reader_valid_one_row, record_one_field)

    after = datetime.now()

    assert all(isinstance(r, record_one_field) for r in result.rows)  # every row is an instance of the expected record model

    assert len(result.rows) == 1  #this reader returns exactly one row
    row = result.rows[0] #so we can safely select only the first one

    assert row.value == "ok"  # row's value matches the source data
    assert row.meta_source == str(source)  # meta_source matches the path passed in
    assert before <= row.meta_extract_date_time <= after  # timestamp was stamped during this call, not before/after it


# invalid rows are handled by pydantic. Just making sure the exception surfaces
def test_load_invalid(reader_invalid_too_long_one_row, record_one_field):
    with pytest.raises(ValidationError):
        BronzeLoader.load(Path("unused"), reader_invalid_too_long_one_row, record_one_field)


# tests that error is handled as a batch instead of failing at the first bad row
def test_load_aggregates_errors_across_multiple_bad_rows(reader_invalid_too_long_two_rows, record_one_field):
    with pytest.raises(ValidationError) as exc_info:
        BronzeLoader.load(Path("unused"), reader_invalid_too_long_two_rows, record_one_field)

    errors = exc_info.value.errors()
    assert len(errors) == 2