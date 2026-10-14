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
    "room_raw": "room_1",
}


# the row is exactly the columns of dev_corrections.corr_journal_entries, in the same order
def test_valid_row():
    row = CorrRecordJournalEntries(**VALID_ROW)

    assert row.model_dump() == {
        "row_id": UUID(ROW_ID),
        "date_time": "2026-09-17 15:13:08",
        "subject": "ONE-A1F0",
        "type": "measurement",
        "ml": "250",
        "ec": "2.4",
        "ph": "5.8",
        "temp": "21.5",
        "notes": None,
        "room_raw": "room_1",
    }
    assert list(row.model_dump().keys()) == list(VALID_ROW.keys())


# corrections metadata is not a column of the row: who reviewed it and when goes to meta_corrections
@pytest.mark.parametrize(
    "column, value", [("meta_reviewed_by", "reviewer"), ("meta_reviewed_date_time", "2026-10-12 16:41:07")]
)
def test_metadata_column_is_refused(column, value):
    with pytest.raises(ValidationError):
        CorrRecordJournalEntries(**VALID_ROW, **{column: value})


# candidate sorts room groups by the text of date_time, so only the shape YYYY-MM-DD HH:MM:SS is accepted,
# even for a value that is a valid timestamp
@pytest.mark.parametrize(
    "date_time",
    ["2026-9-17 15:02:12", "2026-09-17 9:02:12", "2026-09-17T15:02:12", "2026-09-17 15:02:12.5", "2026-09-17 15:02"],
)
def test_date_time_in_another_shape_is_refused(date_time):
    with pytest.raises(ValidationError):
        CorrRecordJournalEntries(**{**VALID_ROW, "date_time": date_time})


# the shape is checked, not the value: a date_time that is not a timestamp is reported by the castable test in dbt
def test_date_time_in_the_shape_that_is_not_a_timestamp_is_accepted():
    row = CorrRecordJournalEntries(**{**VALID_ROW, "date_time": "2026-09-17 25:00:00"})

    assert row.date_time == "2026-09-17 25:00:00"


# the measurements are text: a value that is not a number is reported by the castable test in dbt, not refused here
def test_measurement_that_is_not_a_number_is_accepted():
    row = CorrRecordJournalEntries(**{**VALID_ROW, "ec": "not a number"})

    assert row.ec == "not a number"


# excel hands numbers over as numbers: the reader turns them into text, the row model does not
def test_measurement_that_is_a_number_is_refused():
    with pytest.raises(ValidationError):
        CorrRecordJournalEntries(**{**VALID_ROW, "ec": 2.4})
