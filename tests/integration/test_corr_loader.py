# the loader with the two tables of a corrections upload: the corrections and their metadata
from functools import partial
from uuid import UUID

import pandas as pd
import pytest
from pydantic import ValidationError

from datawarehouse.loaders.loader import Loader
from datawarehouse.readers.reader_excel import ExcelReader
from datawarehouse.records.corr_record_journal_entries import CorrRecordJournalEntries
from datawarehouse.records.meta_record import MetaRecord

ROW_ID_1 = "0199d8a4-7c7e-7b3a-9d5e-2f1c8a6b4e10"
ROW_ID_2 = "0199d8a4-7c7e-7b3a-9d5e-2f1c8a6b4e11"

CORRECTIONS = [
    {
        "row_id": ROW_ID_1,
        "date_time": "2026-09-17 15:13:08",
        "subject": "ONE-A1F0",
        "type": "measurement",
        "ml": 250,
        "ec": 2.4,
        "ph": 5.8,
        "temp": 21.5,
        "notes": None,
        "room_raw": "room_1",
    },
    {
        "row_id": ROW_ID_2,
        "date_time": "2026-09-17 15:14:10",
        "subject": "ONE-A1F0",
        "type": "measurement",
        "ml": None,
        "ec": 2.5,
        "ph": 5.9,
        "temp": None,
        "notes": "refilled",
        "room_raw": None,
    },
]

# one row per row_id and kind, with the columns of the meta table
METADATA = [
    {"row_id": ROW_ID_1, "dataset": "journal_entries", "kind": "reviewed_by", "description": "reviewer"},
    {
        "row_id": ROW_ID_1,
        "dataset": "journal_entries",
        "kind": "reviewed_date_time",
        "description": "2026-10-12 16:41:07",
    },
    {"row_id": ROW_ID_2, "dataset": "journal_entries", "kind": "reviewed_by", "description": "reviewer"},
    {
        "row_id": ROW_ID_2,
        "dataset": "journal_entries",
        "kind": "reviewed_date_time",
        "description": "2026-10-12 16:41:07",
    },
]


def write_workbook(path, corrections, metadata):
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame(corrections).to_excel(writer, sheet_name="corrected", index=False)
        pd.DataFrame(metadata).to_excel(writer, sheet_name="meta_corrections", index=False)
    return path


@pytest.fixture
def workbook(tmp_path):
    return write_workbook(tmp_path / "corrections.xlsx", CORRECTIONS, METADATA)


def test_load_corrections(workbook):
    result, _ = Loader.load(workbook, partial(ExcelReader, "corrected"), CorrRecordJournalEntries)

    assert all(isinstance(r, CorrRecordJournalEntries) for r in result.rows)
    assert [r.row_id for r in result.rows] == [UUID(ROW_ID_1), UUID(ROW_ID_2)]
    # the row holds the correction and nothing else: its metadata is not a column of the row
    assert list(result.rows[0].model_dump().keys()) == list(CORRECTIONS[0].keys())


# the metadata arrives as rows of its own, python does not split a correction into them
def test_load_metadata(workbook):
    result, _ = Loader.load(workbook, partial(ExcelReader, "meta_corrections"), MetaRecord)

    assert all(isinstance(r, MetaRecord) for r in result.rows)
    assert [r.model_dump() for r in result.rows] == [{**row, "row_id": UUID(row["row_id"])} for row in METADATA]


# a fact is recorded only when there is something to say
def test_load_metadata_with_an_empty_description_is_refused(tmp_path):
    metadata = [{**METADATA[0], "description": None}, *METADATA[1:]]
    workbook = write_workbook(tmp_path / "corrections.xlsx", CORRECTIONS, metadata)

    with pytest.raises(ValidationError):
        Loader.load(workbook, partial(ExcelReader, "meta_corrections"), MetaRecord)
