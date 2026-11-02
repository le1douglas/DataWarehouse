# the loader with bronze row models
import csv
from pathlib import Path

import pytest
from pydantic import ValidationError

from datawarehouse.config import JOURNAL_ENTRIES_CSV
from datawarehouse.loaders.loader import Loader
from datawarehouse.readers.reader_csv import CSVReader
from datawarehouse.records.brnz_record_journal_entries import BrnzRecordJournalEntries


def test_load_valid(reader_valid_one_row, record_one_field):
    source = Path("some/path/to/file.csv")

    result = Loader.load(reader_valid_one_row().read(source), record_one_field)

    assert all(
        isinstance(r, record_one_field) for r in result.rows
    )  # every row is an instance of the expected record model

    assert len(result.rows) == 1  # this reader returns exactly one row
    row = result.rows[0]  # so we can safely select only the first one

    # the row holds the source data and nothing else
    assert row.model_dump() == {"value": "ok"}


# the bronze row model of the journal entries is exactly the columns of the csv, in the same order
def test_load_journal_entries_sample_csv():
    with JOURNAL_ENTRIES_CSV.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))

    result = Loader.load(CSVReader.read(JOURNAL_ENTRIES_CSV), BrnzRecordJournalEntries)

    assert len(result.rows) == 40
    assert list(result.rows[0].model_dump().keys()) == header


# invalid rows are handled by pydantic. Just making sure the exception surfaces
def test_load_invalid(reader_invalid_too_long_one_row, record_one_field):
    with pytest.raises(ValidationError):
        Loader.load(reader_invalid_too_long_one_row().read(Path("unused")), record_one_field)


# tests that error is handled as a batch instead of failing at the first bad row
def test_load_aggregates_errors_across_multiple_bad_rows(reader_invalid_too_long_two_rows, record_one_field):
    with pytest.raises(ValidationError) as exc_info:
        Loader.load(reader_invalid_too_long_two_rows().read(Path("unused")), record_one_field)

    errors = exc_info.value.errors()
    assert len(errors) == 2
