from uuid import UUID

import pytest
from pydantic import ValidationError

from datawarehouse.meta_record import MetaRecord

ROW_ID = "0199d8a4-7c7e-7b3a-9d5e-2f1c8a6b4e10"


def test_valid_row():
    row = MetaRecord(row_id=ROW_ID, dataset="journal_entries", kind="source", description="some/path/to/file.csv")

    assert row.model_dump() == {
        "row_id": UUID(ROW_ID),
        "dataset": "journal_entries",
        "kind": "source",
        "description": "some/path/to/file.csv",
    }


# a fact is recorded only when there is something to say
def test_empty_description_is_refused():
    with pytest.raises(ValidationError):
        MetaRecord(row_id=ROW_ID, dataset="journal_entries", kind="source", description="")


def test_description_longer_than_the_column_is_refused():
    with pytest.raises(ValidationError):
        MetaRecord(row_id=ROW_ID, dataset="journal_entries", kind="source", description="-" * 401)
