from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from datawarehouse.records.corr_record_journal_entries import CorrRecordJournalEntries

ROW_ID = "0199d8a4-7c7e-7b3a-9d5e-2f1c8a6b4e10"

VALID_ROW = {
    "row_id": ROW_ID,
    "date_time": "2026-09-17 15:13:08",
    "subject": "ONE-A1F0",
    "type": "measurement",
    "ml": "250",
    "ec": "2.4",
    "ph": "5.8",
    "temp": "21.5",
    "notes": None,
    "room": "room_1",
}


# the row is exactly the columns of dev_corrections.corr_journal_entries, in the same order
def test_valid_row():
    row = CorrRecordJournalEntries(**VALID_ROW)

    assert row.model_dump() == {
        "row_id": UUID(ROW_ID),
        "date_time": datetime(2026, 9, 17, 15, 13, 8),
        "subject": "ONE-A1F0",
        "type": "measurement",
        "ml": Decimal("250"),
        "ec": Decimal("2.4"),
        "ph": Decimal("5.8"),
        "temp": Decimal("21.5"),
        "notes": None,
        "room": "room_1",
    }
    assert list(row.model_dump().keys()) == list(VALID_ROW.keys())


# corrections metadata is not a column of the row: who reviewed it and when goes to meta_corrections
@pytest.mark.parametrize(
    "column, value", [("meta_reviewed_by", "reviewer"), ("meta_reviewed_date_time", "2026-10-12 16:41:07")]
)
def test_metadata_column_is_refused(column, value):
    with pytest.raises(ValidationError):
        CorrRecordJournalEntries(**VALID_ROW, **{column: value})


# unlike bronze, corrections are typed
def test_measurement_that_is_not_a_number_is_refused():
    with pytest.raises(ValidationError):
        CorrRecordJournalEntries(**{**VALID_ROW, "ec": "not a number"})
