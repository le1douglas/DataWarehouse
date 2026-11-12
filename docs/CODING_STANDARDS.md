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
  | `dw_bronze` | `brnz_` for the raw tables, `stg_` for the staging views |
  | `dw_audit` | `aud_` |
  | `dw_silver` | `slvr_` for the datasets, `ref_` for the reference data |
  | `dw_snapshots` | `snap_` |
  | `dw_seeds` | `seed_` |
  | `dw_gold` | `dim_` for the dimensions, `fct_` for the facts |

- A prefix never contains an underscore: the prefix ends at the first `_`, the detail starts at `__`. Prefixes do not need the same length.
- Tables and dbt models: `<prefix>_<dataset>` (`dw_bronze.brnz_journal_entries`, `slvr_journal_entries`). The dbt file name is the relation name; no `alias` and no `generate_alias_name` or `generate_schema_name` override. The folder decides materialisation and schema in `dbt_project.yml`.
- dbt sources are named after the schema and the table: `source("dw_bronze", "brnz_journal_entries")`.
- Data tests of a dataset's rows live in `models/staging/stg_<dataset>.yml`, next to its columns and types. Data tests of the file (shape, row count) live in `models/sources.yml`. Use dbt_expectations, dbt_utils and Elementary's `_with_context` tests, which return whole rows: Elementary stores what a test selects. Severity `error` is the default, set for every data test in `dbt_project.yml`. A data test that only informs and must not refuse the upload, such as `warn_overwritten_rows`, sets `severity: warn` in its own config, with a comment that says why.
- Every data test sets `config.meta.description`, the message the user sees: it says what must be true of the value, and the value itself comes from the file.
- `dw_audit.aud_issues` is the one view of what failed, warned or errored, read from Elementary's tables: `invocation_id, load_id, status, dataset, row_id, kind, target_column, description`. A file failure and an error have a null `row_id`.
- The columns and types of a dataset are declared only in `models/staging/stg_<dataset>.yml`, every column with its `data_type`, next to its data tests. A type has no size: `text`, not `varchar(50)`; `numeric`, not `numeric(4,2)`. `cast_select` casts inside a `case`, which drops the size, so the view would not match its contract. A limit is a rule like any other: a data test in staging that reports the row, such as `length(strain) <= 50`. Gold may present sized types. Staging and gold enforce their contract for the whole folder in `dbt_project.yml`, so a model there fails to build until every column is declared with its type; silver and audit have none. `stg_<dataset>.sql` is a hand-written CTE, the only per-source code, then `{{ cast_select("<cte>") }}`, which reads the model's own yml and casts every column except `row_id`: a value that cannot be cast becomes null and fails `not_null`. `slvr_<dataset>.sql` is `select * from {{ ref("stg_<dataset>") }}`: silver takes its types from staging, and `on_schema_change: fail` stops the build when they change. `slvr_<dataset>.yml` is documentation, descriptions with no types, tests or constraints, plus one setting: `unique_key`, the business key, the only place it is declared. `unique_business_key_in_load_and_silver` (which takes no columns), `warn_overwritten_rows` and `unique_key_index` all read it from there. Any other set of columns that must be unique together is a `unique_columns_in_load_and_silver` test in the staging yml, with its columns written there; the business-key test is a wrapper of it. Data tests are used instead of constraints: the only constraint in silver is the `row_id` primary key (`macros/primary_key.sql`), and the index on `unique_key` is a plain one, for speed (`macros/unique_key_index.sql`). Nothing writes to the warehouse outside `dbt build`, so a constraint would only repeat a test.
- Python: one class per file, file in snake case, class in PascalCase. Test files are `test_<module>.py`, with a name that is unique across `tests/`.
- Snapshots are the exception to the layer prefix: `snap_<recorded table>`, the full name of the one table it records (`snap_slvr_journal_entries`). A snapshot mirrors that table exactly, with no join, filter or derived column; anything combined from several snapshots is a view on top of them. Its `unique_key` is the primary key of the recorded table, its strategy is `check` on all columns, `hard_deletes` is `new_record`. dbt's columns are renamed to `meta_valid_from`, `meta_valid_to` (null on the current version), `meta_version_id`, `meta_updated_at` and `meta_is_deleted`. Its times are `timestamptz` (`macros/snapshot_get_time.sql`). A snapshot is kept only for a table whose rows can change, so bronze, which only holds accepted rows, has none.
- Seeds: `seeds/seed_<name>.csv`, plain data with no yml and no tests. dbt infers each type, except `room`, which is `text` in every seed (`+column_types` in `dbt_project.yml`: dbt has no way to set every column at once, and a seed without that column logs a warning). A csv is named after what it holds (`seed_relative_position_values`). The reference data is one view per seed or combination of seeds in `models/ref/`, `ref_<name>` in `dw_silver`: it selects from the seeds (`ref_rooms`) or combines their rows (`ref_absolute_positions`), and its yml holds every data test of the reference data, written once. A part of a `ref_` is not a view of its own: a test against only some of its rows uses `relationships_where_with_context` (`tests/generic/`) with a `to_condition`, such as a plants batch's room against `ref_rooms` where `assigned_stage = 'flowering'`. Staging and silver test against the `ref_` models, gold publishes them: each `dim_<name>` is a view that selects from its `ref_`, with a contract (names and types) and descriptions, and no data tests. Gold is the only layer the readers use, so a `dim_` exists even when it equals its `ref_`; it is free to reshape it, and staging and silver never depend on gold. A fact's key, nulls and ranges are guarded by the staging tests of its dataset, and its `relationships` tests point at the dimensions. Silver has no foreign key to a `ref_`: a view has no constraints, and recreating a table drops every foreign key pointing at it with `CASCADE`, and an incremental silver never creates its constraints again. Instead the `relationships` test is on staging and judges the load: a load is judged once, so a row removed from a seed later does not fail rows already in silver. `slvr_<dataset>.sql` declares each `ref_` with `-- depends_on: {{ ref("ref_<name>") }}`: `dbt build` skips a model after a failed test only when every model the test reads is upstream of it, so without these a failed relationship test lets the load into silver. After a seed change, run a whole `dbt build` without the var, never `dbt build --select seed_<name>+`: that selects silver but not staging's tests, so silver inserts whatever load staging last held, also a refused one. After a seed's types change, run `dbt seed --full-refresh` once.
- Constraints: primary key `pk_<table>` (`pk_brnz_journal_entries`). This name is for the hand-written DDL. dbt models do not name their constraints: dbt ignores the name of a column-level constraint, and a named primary key clashes with the old table's index on every rebuild. Nothing refers to the generated names, which can change between builds.

## SQL style

- dbt models: a chain of CTEs named with a verb (`identify_room_index`, `assign_position`), each doing one thing, with a lowercase `--` comment saying why. The final select lists columns explicitly so helper columns are not exposed.
- Do not repeat logic across CTEs: compute a value once and reuse it.
- Repeated column lists go in a Jinja `{% set %}` list and a loop.
- `Database/*.sql` (hand-written DDL): uppercase keywords, `CREATE ... IF NOT EXISTS`. These scripts are not formatted by any tool.
- There is no SQL linter, and `sqlfmt` is the only SQL tool: do not add `sqlfluff` or another formatter next to it. The scripts in `Database` are not formatted by any tool.


## Python style

- Comments are lowercase `# ` lines above the code they explain.
- Database errors are caught per exception type, printed with context, and re-raised.
- A function used only inside its module starts with `_`.

## Webapps

The NiceGUI app in `src/webapps`, the home of the data collection programs, an empty page for now.
