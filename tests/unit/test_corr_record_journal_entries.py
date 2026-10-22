from uuid import UUID

import pytest
from pydantic import ValidationError

from datawarehouse.records.corr_record_journal_entries import CorrRecordJournalEntries

ROW_ID = "0199d8a4-7c7e-7b3a-9d5e-2f1c8a6b4e10"

VALID_ROW = {
    "row_id": ROW_ID,
    "date_time": "2026-09-17T15:13:08 Europe/Amsterdam",
    "subject": "ONE-A1F0",
    "type": "measurement",
    "ml": "250",
    "ec": "2.4",
    "ph": "5.8",
    "temp": "21.5",
    "notes": None,
    "room_raw": "room_1",
}


# the row is exactly the columns of dw_corrections.corr_journal_entries, in the same order
def test_valid_row():
    row = CorrRecordJournalEntries(**VALID_ROW)

    assert row.model_dump() == {
        "row_id": UUID(ROW_ID),
        "date_time": "2026-09-17T15:13:08 Europe/Amsterdam",
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


# date_time is not checked here, in any format: a value that cannot be cast, or has no time zone written, is reported
# by the castable test in dbt
@pytest.mark.parametrize(
    "date_time",
    [
        "2026-09-17T15:13:08.363212 Europe/Amsterdam",
        "2026-09-17T13:13:08Z",
        "2026-09-17 15:13:08",
        "2026-09-17 25:00:00 Europe/Amsterdam",
    ],
)
def test_date_time_is_accepted_as_it_is(date_time):
    row = CorrRecordJournalEntries(**{**VALID_ROW, "date_time": date_time})

    assert row.date_time == date_time


# the measurements are text: a value that is not a number is reported by the castable test in dbt, not refused here
def test_measurement_that_is_not_a_number_is_accepted():
    row = CorrRecordJournalEntries(**{**VALID_ROW, "ec": "not a number"})

    assert row.ec == "not a number"


# excel hands numbers over as numbers: the reader turns them into text, the row model does not
def test_measurement_that_is_a_number_is_refused():
    with pytest.raises(ValidationError):
        CorrRecordJournalEntries(**{**VALID_ROW, "ec": 2.4})
