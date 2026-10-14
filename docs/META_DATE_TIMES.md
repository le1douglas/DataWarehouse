# Date-times in the meta tables

Every meta table holds facts as `(row_id, kind, description)`. This file lists the facts whose description is a
date-time, and how each one behaves.

## Overview

| Meta table | `kind` | Written by | Clock | Written when | Changes later? |
|---|---|---|---|---|---|
| `dev_bronze.meta_bronze` | `extract_date_time` | Python, `CSVReader` | Python `datetime.now()`, local time of the machine running the load | When the CSV is read, just before the insert. The same value for every row of the file | No: bronze only inserts |
| `dev_staging.meta_staging` | `staging_date_time` | dbt, incremental append | Postgres `localtimestamp(0)`, session time zone | The first `dbt build` that sees the row | No, except `--full-refresh` |
| `dev_candidate.meta_candidate` | `candidate_date_time` | dbt, incremental append, from `stg_journal_entries__cast` | Postgres `localtimestamp(0)` | The first `dbt build` that sees the row, whether or not it passes the data tests | No, except `--full-refresh` |
| `dev_silver.meta_silver` | `silver_date_time` | dbt, incremental append, from `slvr_journal_entries` | Postgres `localtimestamp(0)` | The first build in which every candidate data test passes | No: a row published again after a correction keeps its first date-time. Except `--full-refresh` |
| `dev_corrections.meta_corrections` | the header of the workbook's last column (the review date-time) | Python, `ExcelReader` | The reviewer's Excel / Power Query | When the reviewer reviewed the row, not when it was loaded | Yes: the load upserts on `(row_id, kind)`, so every upload of the row overwrites it |

The cast errors in `meta_staging` (`kind = 'failed_cast'`) are not date-times. They are deleted and written again
on every build.

## What the date-times mean

For bronze, staging, candidate and silver the date-time is when the row first entered the layer, whether or not it
got any further. A row is stamped in staging even with cast errors, and in candidate even when it fails a data test.
Silver is the exception by construction: entering silver is itself the success, so a row is stamped there only once
every test passes. Silver is all or nothing, so one failing row delays the stamp of every new row.

Corrections is not an entry time. It is the last time the reviewer reviewed the row.

### First build, not first visible

The staging and candidate models are views on bronze, so once they exist a row loaded into bronze is visible in them
immediately. The date-time is written only by the next `dbt build`. A row loaded on Monday and built on Wednesday
has Wednesday as its staging and candidate date-time. The meaning is "the first build that processed the row", not
"the first moment the row could be queried in the layer". Silver is a table, so there the two are the same.

### A failing build

Every dbt model commits in its own transaction, and a failure only skips the models downstream of it. Models that
already finished are not rolled back.

- A candidate data test fails: `meta_staging` and `meta_candidate` are stamped, silver and `meta_silver` are skipped.
- `meta_candidate` fails: `meta_staging` is still stamped, neither depends on the other.
- `meta_staging` fails: its pre_hook delete and its insert are one transaction, so the cast errors are rolled back
  with it, not lost. `meta_candidate` still runs.
- The unguarded `date_time` cast fails: `stg_journal_entries` is ephemeral and inlined in every model that reads it,
  so every staging and candidate model fails and no meta table is stamped.

## Caveats

- `dbt build --full-refresh` drops `meta_staging`, `meta_candidate` and `meta_silver` and stamps every row with the
  time of that build. The first-entry date-times are lost.
- Two clocks: bronze uses Python's clock, staging, candidate and silver use Postgres. They agree only if the Postgres
  session time zone is `Europe/Amsterdam`.
- The descriptions have the format `YYYY-MM-DD HH24:MI:SS`, without a time zone, also in silver.
- The corrections date-time is not normalised: its `kind` is the column header, because `ExcelReader` splits the
  metadata by position, and its description is `str()` of whatever pandas reads from the cell. It can carry fractional
  seconds and nothing checks that it is a date-time.
