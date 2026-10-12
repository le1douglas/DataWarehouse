import pytest
from pydantic import ValidationError

from datawarehouse.record_set import RecordSet


def test_not_empty_no_row(record_one_field):
    with pytest.raises(ValidationError, match="must contain at least one row"):
        RecordSet[record_one_field](rows=[])


def test_not_empty_one_row(record_one_field):
    row = record_one_field(
        value="ok",
    )

    RecordSet[record_one_field](rows=[row])  # should not raise
