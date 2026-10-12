# the loader with bronze row models
import csv
from pathlib import Path

import pytest
from pydantic import ValidationError

from datawarehouse.brnz_record_journal_entries import BrnzRecordJournalEntries
from datawarehouse.config import JOURNAL_ENTRIES_CSV
from datawarehouse.loader import Loader
from datawarehouse.reader_csv import CSVReader


def test_load_valid(reader_valid_one_row, record_one_field):
    source = Path("some/path/to/file.csv")

    result, _ = Loader.load(source, reader_valid_one_row, record_one_field)

    assert all(
        isinstance(r, record_one_field) for r in result.rows
    )  # every row is an instance of the expected record model

    assert len(result.rows) == 1  # this reader returns exactly one row
    row = result.rows[0]  # so we can safely select only the first one

    # the row holds the source data and nothing else: bronze metadata is not a column of the row
    assert row.model_dump() == {"value": "ok"}


# the bronze row model of the journal entries is exactly the columns of the csv, in the same order
def test_load_journal_entries_sample_csv():
    with JOURNAL_ENTRIES_CSV.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))

    result, _ = Loader.load(JOURNAL_ENTRIES_CSV, CSVReader, BrnzRecordJournalEntries)

    assert len(result.rows) == 104
    assert list(result.rows[0].model_dump().keys()) == header


# a bronze load has two metadata rows for every row loaded: from where and when
def test_load_journal_entries_metadata():
    _, meta_result = Loader.load(JOURNAL_ENTRIES_CSV, CSVReader, BrnzRecordJournalEntries)

    assert len(meta_result.rows) == 208
    assert [(r.dataset, r.kind) for r in meta_result.rows[:2]] == [
        ("journal_entries", "source_metadata"),
        ("journal_entries", "extract_date_time"),
    ]
    assert meta_result.rows[0].description == str(JOURNAL_ENTRIES_CSV)


# invalid rows are handled by pydantic. Just making sure the exception surfaces
def test_load_invalid(reader_invalid_too_long_one_row, record_one_field):
    with pytest.raises(ValidationError):
        Loader.load(Path("unused"), reader_invalid_too_long_one_row, record_one_field)


# tests that error is handled as a batch instead of failing at the first bad row
def test_load_aggregates_errors_across_multiple_bad_rows(reader_invalid_too_long_two_rows, record_one_field):
    with pytest.raises(ValidationError) as exc_info:
        Loader.load(Path("unused"), reader_invalid_too_long_two_rows, record_one_field)

    errors = exc_info.value.errors()
    assert len(errors) == 2
