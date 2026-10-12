import pytest

from datawarehouse.corr_record_journal_entries import CorrRecordJournalEntries
from datawarehouse.meta_record import MetaRecord
from datawarehouse.record_set import RecordSet
from datawarehouse.sql_postgres_database import PostgreSQLDatabase

ROW_ID_1 = "0199d8a4-7c7e-7b3a-9d5e-2f1c8a6b4e10"
ROW_ID_2 = "0199d8a4-7c7e-7b3a-9d5e-2f1c8a6b4e11"


# no server listens on this port: a test that passes did not reach the database
@pytest.fixture
def unreachable_database():
    return PostgreSQLDatabase(
        db_server="localhost", db_name="unused", db_user="unused", db_password="unused", db_port=1
    )


def correction(row_id):
    return CorrRecordJournalEntries(
        row_id=row_id,
        date_time="2026-09-17 15:13:08",
        subject="ONE-A1F0",
        type=None,
        ml=None,
        ec=None,
        ph=None,
        temp=None,
        notes=None,
        room=None,
    )


def metadata(row_id):
    return MetaRecord(row_id=row_id, dataset="journal_entries", kind="reviewed_by", description="reviewer")


# the two tables of an upload are about the same journal entries.
# refused before anything is sent to the database
@pytest.mark.parametrize(
    "correction_row_ids, metadata_row_ids, refused_row_id",
    [
        ([ROW_ID_1, ROW_ID_2], [ROW_ID_1], ROW_ID_2),  # a correction without metadata
        ([ROW_ID_1], [ROW_ID_1, ROW_ID_2], ROW_ID_2),  # metadata without a correction
    ],
)
def test_corrections_and_metadata_about_different_row_ids_are_refused(
    unreachable_database, correction_row_ids, metadata_row_ids, refused_row_id
):
    record_set = RecordSet(rows=[correction(row_id) for row_id in correction_row_ids])
    meta_record_set = RecordSet(rows=[metadata(row_id) for row_id in metadata_row_ids])

    with pytest.raises(ValueError, match=refused_row_id):
        unreachable_database.load_to_dev_corrections(
            "corr_journal_entries", record_set, ["row_id"], "meta_corrections", meta_record_set
        )
