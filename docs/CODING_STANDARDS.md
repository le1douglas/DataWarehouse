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
  | `dw_silver` | `slvr_` |
  | `dw_snapshots` | `snap_` |
  | `dw_seeds` | `seed_` |
  | `dw_gold` | `dim_` |

- A prefix never contains an underscore: the prefix ends at the first `_`, the detail starts at `__`. Prefixes do not need the same length.
- Tables and dbt models: `<prefix>_<dataset>` (`dw_bronze.brnz_journal_entries`, `slvr_journal_entries`). The dbt file name is the relation name; no `alias` and no `generate_alias_name` or `generate_schema_name` override. The folder decides materialisation and schema in `dbt_project.yml`.
- dbt sources are named after the schema and the table: `source("dw_bronze", "brnz_journal_entries")`.
- Data tests of a dataset's rows live in `models/staging/stg_<dataset>.yml`, which holds only data tests. Data tests of the file (shape, row count) live in `models/sources.yml`. Use dbt_expectations, dbt_utils and Elementary's `_with_context` tests, which return whole rows: Elementary stores what a test selects. Severity `error` is the default, set for every data test in `dbt_project.yml`. A data test that only informs and must not refuse the upload, such as `unique_across_accepted_uploads`, sets `severity: warn` in its own config, with a comment that says why.
- Every data test sets `config.meta.description`, the message the user sees: it says what must be true of the value, and the value itself comes from the file.
- `dw_audit.aud_failures` is the one view of what failed, read from Elementary's tables: `invocation_id, dataset, row_id, kind, target_column, description`. A file failure has a null `row_id`.
- The columns and types of silver are declared only in `models/silver/slvr_<dataset>.yml`, every column with its `data_type`, with `contract: {enforced: true}`. `slvr_<dataset>.sql` is `select * from {{ ref("stg_<dataset>") }}`. `stg_<dataset>.sql` is a hand-written CTE, the only per-source code, then `{{ cast_select("<cte>", "<dataset>") }}`, which reads the yml and casts every column except `row_id`: a value that cannot be cast becomes null and fails `not_null`. Silver has primary key, unique, foreign key, not null and check constraints as the last guard; the data tests are what reports a bad row, and the column names repeat in the two files on purpose.
- Python: one class per file, file in snake case (`brnz_record_journal_entries.py`, `reader_csv.py`), classes `<Prefix>Record<Dataset>` (`BrnzRecordJournalEntries`), `<Format>Reader` (`CSVReader`). Test files are `test_<module>.py`, with a name that is unique across `tests/unit` and `tests/integration`.
- Snapshots are the exception to the layer prefix: `snap_<recorded table>`, the full name of the one table it records (`snap_slvr_journal_entries`). A snapshot mirrors that table exactly, with no join, filter or derived column; anything combined from several snapshots is a view on top of them. Its `unique_key` is the primary key of the recorded table, its strategy is `check` on all columns, `hard_deletes` is `new_record`. dbt's columns are renamed to `meta_valid_from`, `meta_valid_to` (null on the current version), `meta_version_id`, `meta_updated_at` and `meta_is_deleted`. Its times are `timestamptz` (`macros/snapshot_get_time.sql`). A snapshot is kept only for a table whose rows can change, so bronze, which only holds accepted rows, has none.
- Seeds: `seeds/seed_<name>.csv`, with every column's type in `column_types` in `seeds/seed_<name>.yml`, so dbt infers none. A seed cannot have constraints, so a model on top of it declares them with `contract: {enforced: true}` (`seed_rooms`, `dim_rooms`). A dimension is a table rebuilt from its seed by every build, not incremental, so it always equals the seed: a row removed from the seed leaves the dimension, and a row in staging that still uses it fails the relationship test. The rebuild drops the foreign keys pointing at it and only rebuilding silver creates them again, so after a refused file silver has no foreign keys until the next accepted one. That is accepted: only that rebuild writes to silver, and it checks every row. A foreign key is declared in the silver yml with `to: ref("<dimension>")`, which also makes silver depend on the dimension, so a failed relationship test skips silver.
- Constraints: primary key `pk_<table>` (`pk_brnz_journal_entries`). This name is for the hand-written DDL. dbt models do not name their constraints: dbt ignores the name of a column-level constraint, and a named primary key clashes with the old table's index on every rebuild. Nothing refers to the generated names, which can change between builds.

## SQL style

- dbt models: a chain of CTEs named with a verb (`identify_room_index`, `assign_position`), each doing one thing, with a lowercase `--` comment saying why. The final select lists columns explicitly so helper columns are not exposed.
- Do not repeat logic across CTEs: compute a value once and reuse it.
- Repeated column lists go in a Jinja `{% set %}` list and a loop.
- `Database/*.sql` (hand-written DDL): uppercase keywords, `CREATE ... IF NOT EXISTS`. These scripts are not formatted by any tool.
- There is no SQL linter, and `sqlfmt` is the only SQL tool: do not add `sqlfluff` or another formatter next to it. The scripts in `Database` are not formatted by any tool.


## Python style

- Comments are lowercase `# ` lines above the code they explain.
- Every row model inherits `Record` (`extra="forbid"`, empty string becomes `None`, a pandas NaN is refused). `Record` has no fields; each model declares its own. A bronze row model is a shape check only: the rules on values are data tests.
- Turning missing values into `None` is the reader's job, not the model's.
- A row model mirrors its SQL table: same column names and order.
- Database errors are caught per exception type, printed with context, and re-raised. Loads run in one transaction.
- A function used only inside its module starts with `_`.

## Webapps

The NiceGUI app in `src/webapps`, the home of the data collection programs, an empty page for now. It does not share code with the loader.
