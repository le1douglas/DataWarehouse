import json
import subprocess
from pathlib import Path
from typing import NamedTuple

from datawarehouse.config import DB_SCHEMA_BRONZE, DBT_PROJECT_DIR
from datawarehouse.databases.sql_postgres_database import PostgreSQLDatabase
from datawarehouse.loaders.loader import UploadRefused
from datawarehouse.records.record_set import RecordSet


class DbtBuild(NamedTuple):
    passed: bool
    # the run, to read its failures with. None when dbt did not get as far as judging the data
    invocation_id: str | None
    # what dbt printed, for a build whose failures cannot be read
    output: str = ""


# dbt's exit codes: 0 everything passed, 1 something failed, 2 dbt itself could not run
def run_dbt_build(select: str) -> DbtBuild:
    run_results = Path(DBT_PROJECT_DIR) / "target" / "run_results.json"
    run_results.unlink(missing_ok=True)  # never read the results of an older run

    build = subprocess.run(
        ["dbt", "--no-use-colors", "build", "--select", select],
        cwd=DBT_PROJECT_DIR,
        capture_output=True,
        text=True,
    )

    if build.returncode == 0:
        return DbtBuild(passed=True, invocation_id=None)

    invocation_id = _read_invocation_id(run_results) if build.returncode == 1 and run_results.exists() else None

    return DbtBuild(passed=False, invocation_id=invocation_id, output=build.stdout)


def _read_invocation_id(run_results: Path) -> str:
    return json.loads(run_results.read_text(encoding="utf-8"))["metadata"]["invocation_id"]


def refused_report(failures: list, row_ids: list, record_set: RecordSet) -> str:
    """The message of a refused upload: the file-level failures, then a line per failing value, in csv order.

    The database knows the row_id, the column and the message. The csv in memory knows the line and the original value,
    so what the user reads is what the file says. The header is line 1, so the n-th row is line n + 2 counting from 0.
    """
    index_of_row_id = {row_id: index for index, row_id in enumerate(row_ids)}
    file_failures = sorted({failure.description for failure in failures if failure.row_id is None})
    row_failures = [failure for failure in failures if failure.row_id in index_of_row_id]
    # a data test can also flag a row of an earlier load, such as the other half of a duplicate. it has no line here
    older_rows = {failure.row_id for failure in failures if failure.row_id not in index_of_row_id} - {None}

    lines = [f"Upload refused: {description}." for description in file_failures]

    failed_rows = {failure.row_id for failure in row_failures}
    if failed_rows:
        lines.append(f"Upload refused: {len(failed_rows)} {'row' if len(failed_rows) == 1 else 'rows'} failed.")

    for failure in sorted(row_failures, key=lambda f: (index_of_row_id[f.row_id], f.target_column or "")):
        index = index_of_row_id[failure.row_id]
        line = index + 2
        if failure.target_column is None:
            lines.append(f"Line {line}: {failure.description}")
        else:
            value = record_set.rows[index].model_dump()[failure.target_column]
            shown = "empty" if value is None else value
            lines.append(f"Line {line}, {failure.target_column} = {shown}: {failure.description}")

    if older_rows:
        lines.append(f"{len(older_rows)} {'row' if len(older_rows) == 1 else 'rows'} already in bronze failed as well.")

    return "\n".join(lines)


# TODO revisit once a proper extract is in place: a load that dies between the insert and the undo leaves its rows in
# bronze, and all this does is say so. they then reach silver with the next accepted upload, or block it if they are bad.
# row_id is a uuidv7, so the rows of one load sit between the lowest and the highest row_id
def _undo(postgres: PostgreSQLDatabase, table_name: str, row_ids: list) -> None:
    try:
        postgres.delete_from_bronze(table_name, row_ids)
    except Exception as error:
        raise UploadRefused(
            f"Upload refused, but its {len(row_ids)} rows are STILL IN BRONZE: they could not be deleted "
            f"({type(error).__name__}). Remove them by hand:\n"
            f"delete from {DB_SCHEMA_BRONZE}.{table_name} where row_id between '{min(row_ids)}' and '{max(row_ids)}';"
        ) from error


def upload(postgres: PostgreSQLDatabase, table_name: str, record_set: RecordSet, select: str) -> None:
    """Load, test, undo: dbt only tests data already in the database, so the file goes in, and comes out if refused.

    select is the dbt selection of this dataset, so another dataset's failure cannot refuse this file.
    Bronze must only hold accepted data: whatever goes wrong after the insert, the rows are deleted again.
    """
    row_ids = postgres.load_to_bronze(table_name, record_set)
    accepted = False

    try:
        build = run_dbt_build(select)
        if build.passed:
            accepted = True
            print(f"Upload accepted: {len(row_ids)} rows")
            return

        failures = postgres.read_failures(build.invocation_id) if build.invocation_id else []
    finally:
        if not accepted:
            _undo(postgres, table_name, row_ids)

    if failures:
        raise UploadRefused(refused_report(failures, row_ids, record_set))

    print(build.output)
    raise UploadRefused("Upload refused: it could not be checked, see the dbt output above.")
