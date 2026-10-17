# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Reminders

Unfinished business. The user parks these deliberately: mention the relevant one when work gets near it, do not start it unprompted.

- **Test suite for the pipeline.** The loops of 2026-10-09 were run by hand. `.scratch/pipeline-test-suite/spec.md` lists every scenario that was run with its observed result, and the ones that were not run with their expected result, as the specification of a suite that runs them on a scratch database.
- **Source names contain `dev_`.** `source("dev_bronze", ...)` writes the environment in every call. Accepted until the prod target comes back, then to be revisited.
- **Corrections loader rules:** reject an upload whose `row_id`s are not in `dev_audit.aud_journal_entries`, reject an upload based on a workbook refreshed before the last corrections load. The audit table does not say when it was taken, and after a partial run it mixes fresh results with older ones.
- **Leftovers after a delete or rename:** dbt does not drop the relation of a deleted model or data test. After the 2026-10-14 rebuild the database is clean, but every later delete or rename leaves one behind.
- **Duplicate keys inside one file** are not checked in `RecordSet`; the database index rejects them. The user accepted failing in SQL for now.
- **Bronze re-load:** bronze has no unique index on the content of a row, so loading the same CSV twice silently duplicates every journal entry under new `row_id`s, and the corrections stay on the old ones. "Skip identical rows, abort on same content with different values" is not implemented.
- **Snapshots, added 2026-10-15:** corrections and `meta_corrections` stay upserted (latest value only), and history is kept by dbt snapshots `snap_corr_journal_entries`, `snap_meta_corrections` and `snap_slvr_journal_entries` in `dev_snapshots` (config in `dbt_project.yml`, one yml per snapshot in `DataWarehouseDbt/snapshots`). The rules are in `docs/CODING_STANDARDS.md`. Checked by hand with test corrections on 2026-10-15, then cleaned up: a build with failing tests snapshots corrections and skips the silver snapshot; an unchanged build adds no version; a changed correction adds one version in each snapshot and closes the old one; a deleted correction adds a version with `meta_is_deleted = 'True'`, which is the current version from then on, so a reader must filter it out. The scenarios run and not run are parts C and D of `.scratch/pipeline-test-suite/spec.md`.
- **`meta_is_deleted` is text** (`'True'` / `'False'`), as dbt creates it, not boolean.
- **Snapshot time zone:** dbt-postgres stamps `meta_valid_from` / `meta_valid_to` with `now()::timestamp without time zone`, ambiguous in the repeated hour in October. Overriding `postgres__snapshot_get_time` to keep `timestamptz` was postponed.
- **Snapshots have no reader:** they are storage only. Views that join them (a correction with its reviewer, for example) are a later step.
- **Snapshot schema changes follow dbt's defaults:** a key moved to a new or renamed column splits the history at that build (old versions are marked deleted), and a column whose type changes (mainly in silver's yml) is not migrated and is fixed by hand when it happens. Dropping the database loses all history; on dev that is accepted.
- **Position test is weak:** it only checks `position_index > 4`. A check that every room group has each position exactly once was suggested, not agreed.
- **Same room twice in a row:** with the new position logic two consecutive rounds in the same room merge into one group of 8, and a correction cannot split them.
- **Corrections behaviour to revisit:** every flagged row is uploaded and gets a correction even if untouched; an empty cell overwrites with null; there is no way to withdraw a correction except SQL.
- **Subject cleaning** (stripping ` - Measurement`) was removed while `subject` was part of the key. It no longer is (the key is `row_id`), so nothing blocks it now. The user will decide on a strategy later.
- **Python gaps:** `ExcelReader` has no error handling (a workbook open in Excel gives a raw `PermissionError`), and there is no test for the upsert. On 2026-10-14, 30 of the Python tests failed because they call APIs that have since changed (the CSV and Excel readers, `Loader.load`, `MetaRecord`, `load_to_dev_corrections`).
- **Hardcoded values:** the workbook path (`CORRECTIONS_WORKBOOK` in `src/datawarehouse/config.py`), the reviewer name in the workbook's Power Query.
- **Outdated files:** `README.md` still describes the prod target, the `experiments` workflow and the old `bronze_to_silver` / `silver_to_gold` folders. `Database/04_select_example.sql`, `Database/05_see_test_results.sql` and `Database/corrections.sql` reference schemas and shapes that no longer exist.
- **Later layers:** gold and `experiments` are postponed, a prod target was removed on purpose and will come back later.

## Conventions

### Working style

- Go one step at a time. Make the change that was asked, report, and wait. Large multi-file changes in one go are not wanted.
- Do not run loads, `dbt build` or anything that writes to the database unless asked. For checks, prefer read-only queries or a transaction that is rolled back.
- The corrections workbook (`journal_entries_corrections.xlsx`, on the Desktop, outside the repo) is the user's. Read it with pandas only, never write to it, and it cannot be opened while Excel has it open.
- Keep the split of responsibilities visible in every change: what Python owns, what the hand-written DDL owns, what dbt owns (see Overview).

### Standards and vocabulary

- Read `docs/CODING_STANDARDS.md` before naming or renaming a table, dbt model, test, column, Python module or class, and before writing SQL or Python. It holds the naming shape, the layer prefixes, and the SQL and Python style.
- Name domain concepts with the terms defined in `docs/GLOSSARY.md`.
- After editing dbt models or tests run `sqlfmt DataWarehouseDbt/models DataWarehouseDbt/tests` from the repo root (config in `pyproject.toml`, line length 120; it is the formatter the dbt Power User extension uses). Do not hand-align SQL, the formatter removes it.
- There is no SQL linter, and `sqlfmt` is the only SQL tool: do not add `sqlfluff` or another formatter next to it. The scripts in `Database` are not formatted by any tool.
- After editing Python run `ruff check --fix` and `ruff format` (config in `pyproject.toml`). Do not hand-align code, the formatter removes it.

### Types and data rules

- Bronze stores everything as text, exactly as received.
- Staging and the corrections table have the same column names and types. Everything is text except `row_id`, including `date_time` and the measurements (`ml`, `ec`, `ph`, `temp`), so a value that cannot be cast can still be corrected.
- Silver's columns and types are declared only in `DataWarehouseDbt/models/silver/slvr_<dataset>.yml`, with an enforced contract. Silver is generated from it by the `silver_select` macro: every column except `row_id` is cast to its `data_type`, without a guard. The data test `aud_<dataset>__castable` (the `aud_castable` macro) checks every value with `pg_input_is_valid` on candidate first, so a bad value is a flagged row and silver is skipped. To change a type, change the yml.
- `date_time` is text in the shape `YYYY-MM-DD HH:MM:SS`: staging turns bronze's `2026-09-16T14:43:01.768170` into it with text rules, without a cast. Bronze always has the form `2026-09-17T15:13:08.363212`, or with fewer decimals (`.36`), so the result always has the shape and there is no data test for it. Corrections must have the same shape: `CorrRecordJournalEntries` refuses any other (a pattern) and the table has the check constraint `ck_corr_journal_entries_date_time`, even for a valid timestamp such as `2026-9-17 15:02:12`. So every `date_time` in candidate has one shape, and candidate orders room groups by its text. Whether it is a valid timestamp is still the castable test's job.
- Datetimes have no time zone anywhere before silver, and are cut to the second. Silver is the only place a zone is assigned, from the `timezone` var (`Europe/Amsterdam`).
- The key of a journal entry is `row_id`, a `uuidv7()` assigned by bronze on insert and carried unchanged through staging, corrections, candidate, audit, silver and Excel. `date_time` and `subject` do not identify a journal entry.
- Empty string means null. The decimal separator is `.`; staging turns a decimal comma into a dot.

## Overview

### Objective

A small bronze/silver data warehouse on local PostgreSQL 18 for sensor measurements (the first source is `journal_entries`, CSV exports from the Bluelab "edenic" app). The design goal is that bad data never reaches silver, and that a human can fix it without touching the source file or bronze.

### Pipeline

The diagram of the pipeline is in `docs/DATA_FLOW_DIAGRAM.md`. Update it when an object or a dependency between objects changes.

- **Bronze and corrections are the two inputs.** Both are filled by Python from outside the warehouse, and dbt reads them without ever changing them. Bronze has meaning on its own: it is the store of all raw data, exactly as received. Corrections has meaning only for journal entries already in the warehouse.
- **Candidate is the proposal, silver is the published result.** `dbt build` runs the tests on candidate and skips silver when any fails, so silver keeps its last good data. Anything that can be wrong, that a test looks at, or that a reviewer needs to see belongs in candidate. Silver only casts every column to the type in its yml and assigns the time zone to `timestamptz` columns, so candidate's column names must be silver's.
- **A correction replaces the whole row.** When a `row_id` exists in corrections, every correctable column comes from the correction. Candidate has no column saying a row was corrected: the review joins `row_id` to `dev_corrections`, so the question has one source. Corrections are applied to staging's text, before the cast, and are judged by the data tests like any other row. They stay in their table and are re-applied on every build; bronze is never modified.
- **Corrections are applied after staging's rules.** A row uploaded exactly as candidate shows it must not change, so a rule that is not safe to run twice (the notes split) has to stay in staging, before the join.
- **Data tests** return `row_id` and `description` (the reason only the test knows, such as the columns that cannot be cast), at most one row per `row_id`, one failure table per test in `dev_audit`. The values are candidate's, read by joining `row_id`.
- **The audit table** `dev_audit.aud_journal_entries` has the shape of a meta table: `row_id, kind, description`, one row per flagged row and failed rule, primary key `pk_aud_<dataset>` on `(row_id, kind)`, with the meta tables' types and constraints (`UUID`, `VARCHAR(50)`, `VARCHAR(400)`, all not null, foreign key `fk_aud_<dataset>_row_id` to bronze). The same macro gives each failure table the primary key `pk_<failure table>` on `row_id`, because dbt creates them without constraints; a test returning a `row_id` twice makes `on-run-end` fail before the audit table is replaced. `kind` is the bare rule (the part of the test name after `__`), `description` comes from the failure table. It has no candidate columns: a reader joins `row_id` to candidate. The `create_audit_table` macro drops and recreates it in `on-run-end` as the union of the failure tables, because a model downstream of candidate is skipped when a data test fails, but only in a run where every data test of the dataset ran to a pass or a fail; after any other run (`dbt run`, `dbt snapshot`, a `--select`, a skipped or errored test) it stays the copy of the last run where they all did, so it never mixes failure tables of different runs, and each dataset's audit table depends only on its own tests; it exists with zero rows when nothing failed. It is a table, so it holds the failures of the last build: a correction or bronze row loaded after the build only shows after the next build, while candidate already shows it. It reads only the failure tables of data tests that still exist in the project. The failure tables stay the source of truth.
- **Review in Excel** reads candidate and the audit table (via the ODBC DSN `PostgreSQL_DataWarehouse`) and produces the `corrected` sheet: `row_id`, the correctable columns as text (`date_time` as `YYYY-MM-DD HH:MM:SS`, `.` as the decimal separator, an empty cell for null), then `meta_reviewed_by` and `meta_reviewed_date_time` (`YYYY-MM-DD HH:MM:SS`) as the last two columns. `ExcelReader` reads every cell as text, and splits off the last two columns by position: their headers become the `kind` in `meta_corrections`.
- **Room and position** are derived in candidate: rows are ordered by `date_time`, a room group starts when the recorded room (`room_raw`, the correctable one) changes, `room` is the room of the group, and the rows of a group get the positions `drip_left`, `drip_right`, `drain_left`, `drain_right`.

### Who owns what

| Owner | Objects |
|---|---|
| Hand-written DDL (`Database/01_create_schemas_and_tables.sql`) | `dev_bronze` and `dev_corrections` schemas and tables, their constraints |
| Python (`src/datawarehouse`) | Reading CSV/Excel, validating rows, loading into those two tables |
| dbt (`DataWarehouseDbt`) | `dev_staging`, `dev_candidate`, `dev_audit`, `dev_silver`, `dev_snapshots` and everything in them. These layers have no meta tables |
| The user, in Excel | The review workbook and its Power Query |

Only a `dev` target exists in `%USERPROFILE%\.dbt\profiles.yml`. Database credentials for Python come from `.env` (`POSTGRESQL_*`), which is not in git.

### Python flow

`<Format>Reader.read()` returns two dataframes with the same rows: the data and its metadata. `CSVReader` stamps the kinds `meta_source` and `meta_extract_date_time`; `ExcelReader` splits off the workbook's last two columns (`meta_reviewed_by`, `meta_reviewed_date_time`). `Loader.load` turns every metadata cell into a `MetaRecord`, validates each row into a `Record` subclass and wraps them in a `RecordSet`, and `PostgreSQLDatabase` writes the rows and their metadata in one transaction: `load_to_dev_bronze` appends, `load_to_dev_corrections` upserts on the primary key.

### Commands

Run from the repo root with the virtual environment active (`.venv\Scripts\Activate.ps1`).

```powershell
# a single python test
python -m pytest tests/unit/test_record.py::test_empty_string_to_null_nan

# dbt (or cd into DataWarehouseDbt and drop --project-dir)
dbt build --project-dir DataWarehouseDbt
dbt build --select stg_journal_entries --project-dir DataWarehouseDbt

# rebuild everything from nothing: drop and create the database, run the 01_ DDL, python -m datawarehouse, dbt build
# (asks for the postgres password as a guard against running it by accident; server, port and user come from .env)
.\.scripts\rebuild.ps1   (local, not in git)

# or only the DDL, on an existing empty DataWarehouse database
psql -U postgres -h localhost -d DataWarehouse -1 -v ON_ERROR_STOP=1 -f Database\01_create_schemas_and_tables.sql

# loads, through the package entry point src\datawarehouse\__main__.py
python -m datawarehouse bronze        # csv -> dev_bronze (append)
python -m datawarehouse corrections   # excel -> dev_corrections (upsert)
.\.scripts\load_corrections.ps1       # the same load, then a full dbt build (local, not in git)
```

The `01_` script prints two transaction warnings because `-1` and the file's own `BEGIN`/`COMMIT` overlap; they are harmless. Dropping the database uses `WITH (FORCE)`, which disconnects every session on it, including open VS Code SQL tabs.

In PowerShell, `psql -c` loses double quotes, so `"DataWarehouse"` or `"position"` arrive unquoted and fail or hit the wrong object. Put such statements in a `.sql` file and run it with `-f`.

Editing a table definition in the `01_` script does not change an existing table. To apply it: check the table is empty, `DROP TABLE ... CASCADE` (this also drops the dbt views on top of it), re-run the `01_` script, then `dbt build` to recreate the views.

dbt-postgres replaces a view by dropping the old one with `CASCADE`, so rebuilding a view alone drops every view on top of it without a warning: `dbt run --select stg_journal_entries` drops `cand_journal_entries`, and the tests then error with "relation does not exist". Select the views downstream too (`--select stg_journal_entries+`, but that also builds silver without its tests, so prefer `dbt build`), or recreate them after with `dbt run --select cand_journal_entries`. Silver is a table and is not affected.

A full loop is: DDL, `load_bronze()`, `dbt build` (tests fail, silver skipped), review in Excel, `load_corrections()`, `dbt build` (silver built). Machine setup (Python, PostgreSQL, ODBC, VS Code, dbt, git) is documented step by step in `README.md`.

## Agent skills

### Issue tracker

Issues and specs live as markdown files under `.scratch/<feature-slug>/` in this repo. See `docs/agents/issue-tracker.md`.

### Domain docs

One context: `GLOSSARY-MAP.md` at the repo root points to `docs/GLOSSARY.md`. There are no ADRs; a new one goes in `docs/adr/`. See `docs/agents/domain.md`.
Do not create a `GLOSSARY.md` in the repo root, instead follow the instructions in `GLOSSARY-MAP.md`.
