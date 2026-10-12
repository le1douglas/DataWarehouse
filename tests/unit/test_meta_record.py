import pytest
from pydantic import ValidationError

from datawarehouse.meta_record import MetaRecord


# the row_id of the row the fact is about is not a field: it lives in the database
def test_valid_row():
    row = MetaRecord(dataset="journal_entries", kind="source", description="some/path/to/file.csv")

    assert row.model_dump() == {
        "dataset": "journal_entries",
        "kind": "source",
        "description": "some/path/to/file.csv",
    }


# a fact is recorded only when there is something to say
def test_empty_description_is_refused():
    with pytest.raises(ValidationError):
        MetaRecord(dataset="journal_entries", kind="source", description="")


def test_description_longer_than_the_column_is_refused():
    with pytest.raises(ValidationError):
        MetaRecord(dataset="journal_entries", kind="source", description="-" * 401)
