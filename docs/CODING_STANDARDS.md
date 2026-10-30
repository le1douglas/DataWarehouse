# Coding standards

How code in this repository is named and written. Domain terms are defined in `docs/GLOSSARY.md`; formatting is done by `sqlfmt` and `ruff` (config in `pyproject.toml`) and is not repeated here.

## Which rules win

- In `src/webapps`, `docs/NICEGUI_STANDARDS.md` is NiceGUI's own standard and is followed as it is: where it and this file disagree, it wins (`logging`, not `print()`). This file adds only what NiceGUI leaves open: names, comments, queries.
- Everywhere else this file holds. `docs/NICEGUI_STANDARDS.md` is not edited to fit the project.

## Naming

- One name per dataset (`journal_entries`, `JournalEntries` in class names), spelled the same everywhere. The shape is `<layer prefix>_<dataset>__<detail>`: the step goes before the dataset, a detail of it (a test rule) after it.
- Schemas are `dw_<layer>`, with the full layer word and the same in every environment: each environment has its own database, so the name does not say which one. `dw_` is dbt's default prefix from the profile's `schema: dw`, and the hand-written DDL uses it too. Everything inside a schema, and everything that refers to it, uses the layer's prefix:

  | Schema | Prefix |
  |---|---|
  | `dw_bronze` | `brnz_` |
  | `dw_corrections` | `corr_` |
  | `dw_staging` | `stg_` |
  | `dw_candidate` | `cand_` |
  | `dw_audit` | `aud_` |
  | `dw_silver` | `slvr_` |
  | `dw_snapshots` | `snap_` |

- A prefix never contains an underscore: the prefix ends at the first `_`, the detail starts at `__`. Prefixes do not need the same length.
- Tables and dbt models: `<prefix>_<dataset>` (`dw_bronze.brnz_journal_entries`, `slvr_journal_entries`). The dbt file name is the relation name; no `alias` and no `generate_alias_name` or `generate_schema_name` override. The folder decides materialisation and schema in `dbt_project.yml`.
- dbt sources are named after the schema and the table: `source("dw_bronze", "brnz_journal_entries")`.
- dbt singular tests: `tests/aud_<dataset>/aud_<dataset>__<rule>.sql`, pointing at the candidate model. Severity `error`, `store_failures` and the `audit` schema are set for every data test in `dbt_project.yml`, not per file. The file name is the name of the failure table in `dw_audit`, and relation names are limited to 63 characters.
- A data test returns three columns, `row_id`, `target_column` and `description`: `select row_id, <column or null::text> as target_column, <reason> as description from {{ ref("cand_<dataset>") }} where ...`, on one candidate model, at most one row per `row_id` and `target_column`. `target_column` is the column the error is in, null when it is in the whole row. `description` is what only the test knows (why the value cannot be cast, the offending value); the row's values are candidate's and are not copied.
- Audit table: `aud_<dataset>` (`dw_audit.aud_journal_entries`), one per candidate model, next to the failure tables `aud_<dataset>__<rule>`. It is created by the `create_audit_table` macro in `on-run-end`, one call per dataset in `dbt_project.yml`, not by a model, as the union of the failure tables: `row_id, kind, target_column, description`, one row per failed rule and column, where `kind` is the `<rule>` part of the data test's name and `target_column` and `description` are those the data test returned. Its columns and constraints are those of the meta tables: `UUID`, `VARCHAR(50)`, `VARCHAR(400)`, all not null, foreign key `fk_aud_<dataset>_row_id` to the dataset's bronze table, plus `target_column VARCHAR(63)`, nullable. The key is the unique constraint `uq_aud_<dataset>` on `(row_id, kind, target_column)` with `NULLS NOT DISTINCT`, not a primary key, which cannot hold the null of a whole-row error.
- Metadata columns start with `meta_` (`meta_reviewed_by` and `meta_reviewed_date_time` in the workbook, and `meta_failed_tests`, which the workbook builds from the audit table's `kind`s). The Excel side filters on this prefix, so a non-`meta_` column of candidate that also exists in staging is treated as correctable.
- The columns and types of silver are declared only in `models/silver/slvr_<dataset>.yml`, every column with its `data_type`, with `contract: {enforced: true}`. `slvr_<dataset>.sql` is `{{ silver_select("<dataset>") }}` and `aud_<dataset>__castable.sql` is `{{ aud_castable("<dataset>") }}`; both read the yml. Every column except `row_id` is cast from text to its `data_type`, a `timestamptz` column also gets the `timezone` var. There are no per-column rules: a candidate column has the name of the silver column it becomes, and a candidate column that is not in the yml is not published.
- From staging onwards the bronze column `tags` is called `room_raw`, the room as recorded (and as corrected). Candidate derives `room`, the room of the room group, which is what silver publishes. Names and comments use "room", "room group" and `room_index`.
- Python: one class per file, file in snake case (`brnz_record_journal_entries.py`, `reader_csv.py`), classes `<Prefix>Record<Dataset>` (`BrnzRecordJournalEntries`), `<Format>Reader` (`CSVReader`). There is one `Loader`, the same for every layer and every reader. Test files are `test_<module>.py`, with a name that is unique across `tests/unit` and `tests/integration`.
- Meta tables are the exception to the layer prefix: `meta_<layer>` with the full layer word (`dw_bronze.meta_bronze`), one per layer for every dataset of the layer. Their row model is `MetaRecord`, without a layer prefix or a dataset, because it is the same for every meta table. Bronze and corrections have no `meta_` columns: their metadata is in `meta_bronze` and `meta_corrections`, and every `kind` starts with `meta_` (`meta_source`, `meta_reviewed_by`), the name the fact would have as a column. A date-time kind ends in `_date_time` (`meta_extract_date_time`, `meta_reviewed_date_time`), and its description is a date-time with its offset (`2026-10-22T14:42:08+02:00`), enforced by `ck_meta_<layer>_description`. Only these two inputs have a meta table; the layers built by dbt have none. The audit table has the shape of a meta table (`row_id, kind, description`) but keeps the `aud_` name, and its `kind` is the bare rule (`castable`), without `meta_`, because a rule is not a column.
- Snapshots are the other exception: `snap_<recorded table>`, the full name of the one table it records (`snap_corr_journal_entries`, `snap_meta_corrections`, `snap_slvr_journal_entries`). A snapshot mirrors that table exactly, with no join, filter or derived column; anything combined from several snapshots is a view on top of them. Its `unique_key` is the primary key of the recorded table, its strategy is `check` on all columns, `hard_deletes` is `new_record`. dbt's columns are renamed to `meta_valid_from`, `meta_valid_to` (null on the current version), `meta_version_id`, `meta_updated_at` and `meta_is_deleted`. Its times are `timestamptz` (`macros/snapshot_get_time.sql`). A snapshot is kept only for a table whose rows can change, so bronze and `meta_bronze`, which are append-only, have none.
- Constraints: primary key `pk_<table>` (`pk_brnz_journal_entries`), foreign key `fk_<table>_<column>` (`fk_corr_journal_entries_row_id`), check `ck_<table>_<column>` (`ck_meta_bronze_description`). The same names are used in the hand-written DDL and in a dbt model's `constraints` (`pk_slvr_journal_entries`).

## SQL style

- The column order of a select is deliberate (it matches the corrections table and the Excel upload) and must not be rearranged.
- dbt models: a chain of CTEs named with a verb (`identify_room_index`, `assign_position`), each doing one thing, with a lowercase `--` comment saying why. The final select lists columns explicitly so helper columns are not exposed.
- Do not repeat logic across CTEs: compute a value once and reuse it.
- Repeated column lists go in a Jinja `{% set %}` list and a loop.
- `Database/*.sql` (hand-written DDL): uppercase keywords, `CREATE ... IF NOT EXISTS`. These scripts are not formatted by any tool.
- There is no SQL linter, and `sqlfmt` is the only SQL tool: do not add `sqlfluff` or another formatter next to it. The scripts in `Database` are not formatted by any tool.


## Python style

- Comments are lowercase `# ` lines above the code they explain.
- Every row model inherits `Record` (`extra="forbid"`, empty string becomes `None`, a pandas NaN is refused). `Record` has no fields; each model declares its own. The metadata of a row is not a field: `BrnzRecord` and `CorrRecord` carry it as `meta_records`, excluded from `model_dump`.
- Turning missing values into `None` is the reader's job, not the model's. A dataframe from CSV and one from Excel must look the same where cells are empty.
- A row model mirrors its SQL table as closely as possible: same column names, order, lengths and nullability.
- Database errors are caught per exception type, printed with context, and re-raised. Loads run in one transaction.
- A function used only inside its module starts with `_`.

## Webapps

The NiceGUI app in `src/webapps`, where a reviewer corrects candidate. It does not share code with the loader.

- One module per job: `main.py` the page, `queries.py` the SQL calls and nothing else, `orchestration.py` dbt (running it, and hearing when any dbt command ends). A custom element is a class in its own file in `ui_elements/`, with its `.vue` file, if it has one, next to it under the same name (`errors_tooltip.py`, `errors_tooltip.vue`, class `ErrorsTooltip`; `submit_button.py`, class `SubmitButton`; `error_jump_buttons.py`, class `ErrorJumpButtons`; `reload_button.py`, class `ReloadButton`). `ui_elements/grid.py`, class `Grid`, holds the AG Grid options and the rules (which column is locked, which row and cell are in error), and owns the errors tooltip and the error jump buttons. An element owns its state and its behavior; the page reaches them only through its methods. `ui_elements/rows_text.py` holds `rows_text`, the one function elements share.
- A rule is decided once in Python, in `Grid`, and sent with the row as a field the grid has no column for (`is_error_row`, `row_errors`, `column_errors`). The JavaScript in the grid options only reads these fields.
- Queries use SQLAlchemy Core `select()` on reflected tables, never `text()`, so SQLAlchemy quotes every name. A function that reads is `select_<what>` (`select_datasets`, `select_aud_errors`), one that writes is named after the statement (`upsert_corrections`). Every value goes to the browser as text: a `uuid` cannot be sent as it is.
- Blocking calls (every query) run in `run.io_bound`, so the page does not freeze for every user.
- The grid is styled with AG Grid's theme parameters (`--ag-*` variables, `color-mix` on them), so it follows dark mode by itself. A custom class or color is used only when no theme parameter fits.
- JavaScript and CSS come in only where NiceGUI's Python API has nothing that fits, as the golden rule of `docs/NICEGUI_STANDARDS.md` allows, each with a comment saying why: the grid's `:`-prefixed options, `GRID_JS` and `GRID_CSS` in `grid.py`, and `.vue` components.
