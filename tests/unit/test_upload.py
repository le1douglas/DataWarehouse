from types import SimpleNamespace

import pandas as pd
import pytest

from datawarehouse.loaders import upload as upload_module
from datawarehouse.loaders.loader import Loader, UploadRefused
from datawarehouse.loaders.upload import DbtBuild, refused_report, upload
from datawarehouse.records.brnz_record_journal_entries import BrnzRecordJournalEntries

COLUMNS = ["date_time", "device", "spot", "ml", "ec", "ph", "temperature", "room"]


def record_set(rows=2):
    row = {column: "1" for column in COLUMNS}
    return Loader.load(pd.DataFrame([row] * rows, dtype=object), BrnzRecordJournalEntries)


def failure(row_id, target_column, description):
    return SimpleNamespace(row_id=row_id, target_column=target_column, description=description)


class FakeDatabase:
    def __init__(self, failures=()):
        self.failures = list(failures)
        self.deleted = None

    def load_to_bronze(self, table_name, rows):
        return ["a", "b"]

    def read_failures(self, invocation_id):
        return self.failures

    def delete_from_bronze(self, table_name, row_ids):
        self.deleted = row_ids


def test_report_gives_line_value_and_message():
    report = refused_report([failure("b", "ml", "ml is wrong")], ["a", "b"], record_set())

    assert report == "Upload refused: 1 row failed.\nLine 3, ml = 1: ml is wrong"


def test_report_counts_rows_not_failures_and_keeps_csv_order():
    failures = [
        failure("b", "ph", "ph is wrong"),
        failure("a", "ml", "ml is wrong"),
        failure("a", None, "the row is wrong"),
    ]

    report = refused_report(failures, ["a", "b"], record_set())

    assert report.splitlines() == [
        "Upload refused: 2 rows failed.",
        "Line 2: the row is wrong",
        "Line 2, ml = 1: ml is wrong",
        "Line 3, ph = 1: ph is wrong",
    ]


def test_report_of_a_file_failure_has_no_line():
    report = refused_report([failure(None, None, "the file must have 20 to 40 rows")], ["a", "b"], record_set())

    assert report == "Upload refused: the file must have 20 to 40 rows."


# a duplicate of an earlier load flags both rows, and the older one has no line in this file
def test_report_counts_rows_of_earlier_loads_without_a_line():
    failures = [failure("b", None, "already measured"), failure("old", None, "already measured")]

    report = refused_report(failures, ["a", "b"], record_set())

    assert report.splitlines() == [
        "Upload refused: 1 row failed.",
        "Line 3: already measured",
        "1 row already in bronze failed as well.",
    ]


def test_report_when_only_rows_of_earlier_loads_failed():
    report = refused_report([failure("old", "ml", "ml is wrong")], ["a", "b"], record_set())

    assert report == "1 row already in bronze failed as well."


def test_upload_accepted_keeps_the_rows(monkeypatch):
    monkeypatch.setattr(upload_module, "run_dbt_build", lambda select: DbtBuild(True, None))
    database = FakeDatabase()

    upload(database, "table", record_set(), "select")

    assert database.deleted is None


def test_upload_refused_deletes_the_rows(monkeypatch):
    monkeypatch.setattr(upload_module, "run_dbt_build", lambda select: DbtBuild(False, "run"))
    database = FakeDatabase([failure("a", "ml", "ml is wrong")])

    with pytest.raises(UploadRefused):
        upload(database, "table", record_set(), "select")

    assert database.deleted == ["a", "b"]


def test_upload_that_could_not_be_checked_deletes_the_rows(monkeypatch):
    monkeypatch.setattr(upload_module, "run_dbt_build", lambda select: DbtBuild(False, None))
    database = FakeDatabase()

    with pytest.raises(UploadRefused, match="could not be checked"):
        upload(database, "table", record_set(), "select")

    assert database.deleted == ["a", "b"]


def test_upload_deletes_the_rows_when_dbt_crashes(monkeypatch):
    def crash(select):
        raise OSError("no dbt")

    monkeypatch.setattr(upload_module, "run_dbt_build", crash)
    database = FakeDatabase()

    with pytest.raises(OSError):
        upload(database, "table", record_set(), "select")

    assert database.deleted == ["a", "b"]


def test_upload_says_so_when_the_rows_cannot_be_deleted(monkeypatch):
    def crash(select):
        raise OSError("no dbt")

    class DatabaseGone(FakeDatabase):
        def delete_from_bronze(self, table_name, row_ids):
            raise ConnectionError("database gone")

    monkeypatch.setattr(upload_module, "run_dbt_build", crash)

    with pytest.raises(UploadRefused) as refused:
        upload(DatabaseGone(), "table", record_set(), "select")

    assert "2 rows are STILL IN BRONZE" in str(refused.value)
    assert "row_id between 'a' and 'b'" in str(refused.value)


def test_a_missing_column_is_refused_by_name():
    row = {column: "1" for column in COLUMNS if column != "temperature"}

    with pytest.raises(UploadRefused, match="temperature"):
        Loader.load(pd.DataFrame([row], dtype=object), BrnzRecordJournalEntries)


def test_an_extra_column_is_ignored():
    row = {column: "1" for column in COLUMNS} | {"extra": "1"}

    result = Loader.load(pd.DataFrame([row], dtype=object), BrnzRecordJournalEntries)

    assert list(result.rows[0].model_dump()) == COLUMNS
