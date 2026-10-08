# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current feature

The manual corrections loop for `journal_entries`: a reviewer fixes flagged rows in Excel, Python uploads them to `dev_corrections`, dbt applies them and rebuilds silver.

- The loop has run end to end three times, the last two on 2026-10-08 from an empty database (drop database, DDL, CSV to bronze, `dbt build`, review in Excel, upload corrections, `dbt build`). The first build fails `aud_journal_entries__position_index_max_4` on 8 rows and skips silver; after the 8 corrections the second build passes and silver is built with 104 rows.
- Last change: the naming convention (see Naming). Every table, model, test, Python module and class got a layer prefix (`brnz_`, `corr_`, `stg_`, `cand_`, `aud_`, `slvr_`), and the third run was done on the new names. The workbook's Power Query reads `dev_audit.aud_journal_entries__position_index_max_4`.
- Before that: the position logic in `DataWarehouseDbt/models/candidate/cand_journal_entries.sql`. A new room group starts only when the room value differs from the room of the row before it, not on every row that has a room. A reviewer can fill the room on all four rows of a group or only on the first one, the result is the same (26 room groups of 4).

Update this section when the focus changes.

## Reminders

Unfinished business. The user parks these deliberately: mention the relevant one when work gets near it, do not start it unprompted.

- **Combined audit view.** One view that unions the per-test failure tables in `dev_audit`, so Excel and the corrections loader read a single object. To be done in dbt, not hand-written DDL. dbt-postgres 1.11.0 drops failure tables with `cascade` (checked in its drop macros), so a view on top of them disappears on every build and has to be recreated; an `on-run-end` hook was suggested. The `__` in the test names separates the table from the rule.
- **Source names contain `dev_`.** `source("dev_bronze", ...)` writes the environment in every call. Accepted until the prod target comes back, then to be revisited.
- **Corrections loader rules that depend on that view:** reject keys that are not in audit, reject an upload based on an audit older than the last corrections load.
- **Duplicate keys inside one file** are not checked in `RecordSet`; the database index rejects them. The user accepted failing in SQL for now.
- **Bronze re-load:** loading the same CSV twice fails on the unique index. "Skip identical rows, abort on same key with different values" is not implemented.
- **Position test is weak:** it only checks `position_index > 4`. A check that every room group has each position exactly once was suggested, not agreed.
- **Same room twice in a row:** with the new position logic two consecutive rounds in the same room merge into one group of 8, and a correction cannot split them.
- **Corrections behaviour to revisit:** every flagged row is uploaded and marked `meta_is_corrected` even if untouched; an empty cell overwrites with null; there is no way to withdraw a correction except SQL.
- **Subject cleaning** (stripping ` - Measurement`) was removed because `subject` is part of the key. The user will decide on a strategy later.
- **Python gaps:** `ExcelReader` has no error handling (a workbook open in Excel gives a raw `PermissionError`), and there are no tests for `ExcelReader`, `CorrLoader`, `CorrRecordJournalEntries` or the upsert.
- **Hardcoded values:** the workbook path in `load_journal_entries.py`, the sheet name `corrected` in `ExcelReader`, the reviewer name in the workbook's Power Query.
- **Outdated files:** `README.md` still describes the prod target, the `experiments` workflow and the old `bronze_to_silver` / `silver_to_gold` folders. `Database/04_select_example.sql`, `Database/05_see_test_results.sql` and `Database/corrections.sql` reference schemas and shapes that no longer exist.
- **Later layers:** gold and `experiments` are postponed, a prod target was removed on purpose and will come back later.

## Conventions

### Working style

- Go one step at a time. Make the change that was asked, report, and wait. Large multi-file changes in one go are not wanted.
- Do not run loads, `dbt build` or anything that writes to the database unless asked. For checks, prefer read-only queries or a transaction that is rolled back.
- The corrections workbook (`journal_entries_corrections.xlsx`, on the Desktop, outside the repo) is the user's. Read it with pandas only, never write to it, and it cannot be opened while Excel has it open.
- Keep the split of responsibilities visible in every change: what Python owns, what the hand-written DDL owns, what dbt owns (see Overview).

### Naming

- One token per business concept (`journal_entries`, `JournalEntries` in class names), spelled the same everywhere. The shape is `<layer prefix>_<token>__<detail>`: the step goes before the token, a detail of the concept (a test rule) after it.
- Schemas keep the full layer word, `dev_<layer>`. Everything inside a schema, and everything that refers to it, uses the layer's prefix:

  | Schema | Prefix |
  |---|---|
  | `dev_bronze` | `brnz_` |
  | `dev_corrections` | `corr_` |
  | `dev_staging` | `stg_` |
  | `dev_candidate` | `cand_` |
  | `dev_audit` | `aud_` |
  | `dev_silver` | `slvr_` |

- A prefix never contains an underscore: the prefix ends at the first `_`, the detail starts at `__`. Prefixes do not need the same length.
- Tables and dbt models: `<prefix>_<token>` (`dev_bronze.brnz_journal_entries`, `slvr_journal_entries`). The dbt file name is the relation name; no `alias` and no `generate_alias_name` or `generate_schema_name` override. The folder decides materialisation and schema in `dbt_project.yml`.
- dbt sources are named after the schema and the table: `source("dev_bronze", "brnz_journal_entries")`.
- dbt singular tests: `aud_<token>__<rule>.sql`, each with `{{ config(severity='error', store_failures=true) }}`, pointing at the candidate model. The file name is the name of the failure table in `dev_audit`, and relation names are limited to 63 characters.
- Metadata columns start with `meta_` (`meta_extract_date_time`, `meta_source`, `meta_cast_errors`, `meta_is_corrected`, `meta_reviewed_by`, `meta_reviewed_date_time`, `meta_silver_date_time`). The Excel side filters on this prefix, so a non-`meta_` column in staging is treated as correctable.
- From staging onwards the bronze column `tags` is called `room`. Use "room", "room group" and `room_index` in names and comments, never "tag".
- Python: one class per file, file in snake case (`brnz_record_journal_entries.py`, `reader_csv.py`), classes `<Prefix>Record<Token>` (`BrnzRecordJournalEntries`), `<Prefix>Loader` (`CorrLoader`), `<Format>Reader`. Test files are `test_<module>.py`, with a name that is unique across `tests/unit` and `tests/integration`.
- Unique key index: `uq_<table>_key` (`uq_brnz_journal_entries_key`).

### SQL style

- dbt models and tests are formatted by `sqlfmt` (config in `pyproject.toml`, line length 120), the formatter the dbt Power User extension uses. After editing them run `sqlfmt DataWarehouseDbt/models DataWarehouseDbt/tests` from the repo root. Do not hand-align SQL, the formatter removes it.
- There is no SQL linter, and `sqlfmt` is the only SQL tool: do not add `sqlfluff` or another formatter next to it. The scripts in `Database` are not formatted by any tool.
- The column order of a select is deliberate (it matches the corrections table and the Excel upload) and must not be rearranged.
- dbt models: lowercase keywords, a chain of CTEs named with a verb (`identify_room_index`, `assign_position`), each doing one thing, with a lowercase `--` comment saying why. The final select lists columns explicitly so helper columns are not exposed.
- Do not repeat logic across CTEs: compute a value once and reuse it.
- Repeated column lists go in a Jinja `{% set %}` list and a loop.
- `Database/*.sql` (hand-written DDL): uppercase keywords, `CREATE ... IF NOT EXISTS`.

### Python style

- Formatting and linting are done by `ruff` (config in `pyproject.toml`): run `ruff check --fix` and `ruff format` after editing Python. Do not hand-align code, the formatter removes it.
- Comments are lowercase `# ` lines above the code they explain.
- Every row model inherits `Record` (`extra="forbid"`, empty string becomes `None`, a pandas NaN is refused). `Record` has no fields; each model declares its own, including the `meta_` ones.
- Turning missing values into `None` is the reader's job, not the model's. A dataframe from CSV and one from Excel must look the same where cells are empty.
- A row model mirrors its SQL table as closely as possible: same column names, order, lengths and nullability.
- Database errors are caught per exception type, printed with context, and re-raised. Loads run in one transaction.

### Types and data rules

- Bronze stores everything as text, exactly as received.
- Staging and the corrections table have the same column names and types, apart from their `meta_` columns. Measurements (`ml`, `ec`, `ph`, `temp`) are numeric in both.
- Casts are guarded with `pg_input_is_valid` in staging: a value that cannot be cast becomes null and is reported in `meta_cast_errors`. The one unguarded cast is the key's `date_time`, which is allowed to fail the whole build.
- Datetimes have no time zone anywhere before silver, and are cut to the second. Silver is the only place a zone is assigned, from the `timezone` var (`Europe/Amsterdam`).
- The key of a journal entry is `date_time` cut to the second plus `subject`, identical in bronze, staging, corrections, candidate, audit and Excel.
- Empty string means null. The decimal separator is `.`; staging turns a decimal comma into a dot.

## Overview

### Objective

A small bronze/silver data warehouse on local PostgreSQL 18 for sensor measurements (the first source is `journal_entries`, CSV exports from the Bluelab "edenic" app). The design goal is that bad data never reaches silver, and that a human can fix it without touching the source file or bronze.

### Pipeline

```
CSV ──python──> dev_bronze.brnz_journal_entries      (text, as received)
                      │ dbt
                      ▼
                dev_staging.stg_journal_entries       (view: auto-fix, guarded casts)
                      │ dbt        dev_corrections.corr_journal_entries <──python── Excel
                      ▼                │
                dev_candidate.cand_journal_entries    (view: corrections override, room groups, positions)
                      │ dbt tests ──> dev_audit.<test>  (failing rows, one table per test)
                      ▼ only if all tests pass
                dev_silver.slvr_journal_entries       (table: published, time zone assigned)
```

- **Candidate is the proposal, silver is the published result.** `dbt build` runs the tests on candidate and skips silver when any fails, so silver keeps its last good data. Anything that can be wrong, that a test looks at, or that a reviewer needs to see belongs in candidate. Silver is close to a plain select.
- **A correction replaces the whole row.** When a key exists in corrections, every correctable column comes from the correction. Corrections stay in their table and are re-applied on every build; bronze is never modified.
- **Review in Excel** reads candidate for context and an audit table for the flagged keys (via the ODBC DSN `PostgreSQL_DataWarehouse`), marks rows `needs_review`, and produces the `corrected` sheet with staging's non-`meta_` columns plus `meta_reviewed_by` and `meta_reviewed_date_time`.
- **Room and position** are derived in candidate: rows are ordered by `date_time`, a room group starts when the room changes, and the rows of a group get the positions `drip_left`, `drip_right`, `drain_left`, `drain_right`.

### Who owns what

| Owner | Objects |
|---|---|
| Hand-written DDL (`Database/03_create_schemas_and_tables.sql`) | `dev_bronze` and `dev_corrections` schemas and tables, their unique indexes |
| Python (`src/datawarehouse`) | Reading CSV/Excel, validating rows, loading into those two tables |
| dbt (`DataWarehouseDbt`) | `dev_staging`, `dev_candidate`, `dev_audit`, `dev_silver` and everything in them |
| The user, in Excel | The review workbook and its Power Query |

Only a `dev` target exists in `%USERPROFILE%\.dbt\profiles.yml`. Database credentials for Python come from `.env` (`POSTGRESQL_*`), which is not in git.

### Python flow

`<Format>Reader.read()` returns a dataframe, a `<Layer>Loader` validates each row into a `Record` subclass and wraps them in a `RecordSet`, and `PostgreSQLDatabase` writes it. `BrnzLoader` stamps `meta_extract_date_time` and `meta_source` and the load appends; `CorrLoader` adds nothing and the load upserts on the key.

### Commands

Run from the repo root with the virtual environment active (`.venv\Scripts\Activate.ps1`).

```powershell
# a single python test
python -m pytest tests/unit/test_record.py::test_empty_string_to_null_nan

# dbt (or cd into DataWarehouseDbt and drop --project-dir)
dbt build --project-dir DataWarehouseDbt
dbt build --select stg_journal_entries --project-dir DataWarehouseDbt

# rebuild the database from nothing: run Database\01_drop_database.sql and 02_create_database.sql
# while connected to the postgres database, then
psql -U postgres -h localhost -d DataWarehouse -1 -v ON_ERROR_STOP=1 -f Database\03_create_schemas_and_tables.sql

# loads: main() currently calls load_corrections() only, load_bronze() is commented out
python src\datawarehouse\load_journal_entries.py
```

The `03_` script prints two transaction warnings because `-1` and the file's own `BEGIN`/`COMMIT` overlap; they are harmless. Dropping the database is refused while VS Code SQL tabs are connected to it.

In PowerShell, `psql -c` loses double quotes, so `"DataWarehouse"` or `"position"` arrive unquoted and fail or hit the wrong object. Put such statements in a `.sql` file and run it with `-f`.

Editing a table definition in the `03_` script does not change an existing table. To apply it: check the table is empty, `DROP TABLE ... CASCADE` (this also drops the dbt views on top of it), re-run the `03_` script, then `dbt build` to recreate the views.

A full loop is: DDL, `load_bronze()`, `dbt build` (tests fail, silver skipped), review in Excel, `load_corrections()`, `dbt build` (silver built). Machine setup (Python, PostgreSQL, ODBC, VS Code, dbt, git) is documented step by step in `README.md`.
