# Coding standards

How code in this repository is named and written. Domain terms are defined in `docs/GLOSSARY.md`; formatting is done by `sqlfmt` and `ruff` (config in `pyproject.toml`) and is not repeated here.

## Naming

- One name per dataset (`journal_entries`, `JournalEntries` in class names), spelled the same everywhere. The shape is `<layer prefix>_<dataset>__<detail>`: the step goes before the dataset, a detail of it (a test rule) after it.
- Schemas keep the full layer word, `dev_<layer>`. Everything inside a schema, and everything that refers to it, uses the layer's prefix:

  | Schema | Prefix |
  |---|---|
  | `dev_bronze` | `brnz_` |
  | `dev_corrections` | `corr_` |
  | `dev_staging` | `stg_` |
  | `dev_candidate` | `cand_` |
  | `dev_audit` | `aud_` |
  | `dev_silver` | `slvr_` |
  | `dev_snapshots` | `snap_` |

- A prefix never contains an underscore: the prefix ends at the first `_`, the detail starts at `__`. Prefixes do not need the same length.
- Tables and dbt models: `<prefix>_<dataset>` (`dev_bronze.brnz_journal_entries`, `slvr_journal_entries`). The dbt file name is the relation name; no `alias` and no `generate_alias_name` or `generate_schema_name` override. The folder decides materialisation and schema in `dbt_project.yml`.
- dbt sources are named after the schema and the table: `source("dev_bronze", "brnz_journal_entries")`.
- dbt singular tests: `tests/aud_<dataset>/aud_<dataset>__<rule>.sql`, pointing at the candidate model. Severity `error`, `store_failures` and the `audit` schema are set for every data test in `dbt_project.yml`, not per file. The file name is the name of the failure table in `dev_audit`, and relation names are limited to 63 characters.
- A data test returns whole, unchanged candidate rows: `select * from {{ ref("cand_<dataset>") }} where ...`, on one candidate model, with no column added, removed or changed, so a failure table shows the reviewer the values of the row that failed.
- Audit table: `aud_<dataset>` (`dev_audit.aud_journal_entries`), one per candidate model, next to the failure tables `aud_<dataset>__<rule>`. It is created by the `create_audit_table` macro in `on-run-end`, one call per dataset in `dbt_project.yml`, not by a model, and its `meta_failed_tests` column holds the `<rule>` part of each data test the row failed.
- Metadata columns start with `meta_` (`meta_is_corrected` in candidate, `meta_failed_tests` in the audit table, `meta_reviewed_by` and `meta_reviewed_date_time` in the workbook). The Excel side filters on this prefix, so a non-`meta_` column of candidate that also exists in staging is treated as correctable.
- The columns and types of silver are declared only in `models/silver/slvr_<dataset>.yml`, every column with its `data_type`, with `contract: {enforced: true}`. `slvr_<dataset>.sql` is `{{ silver_select("<dataset>") }}` and `aud_<dataset>__castable.sql` is `{{ aud_castable("<dataset>") }}`; both read the yml. Every column except `row_id` is cast from text to its `data_type`, a `timestamptz` column also gets the `timezone` var. There are no per-column rules: a candidate column has the name of the silver column it becomes, and a candidate column that is not in the yml is not published.
- From staging onwards the bronze column `tags` is called `room_raw`, the room as recorded (and as corrected). Candidate derives `room`, the room of the room group, which is what silver publishes. Names and comments use "room", "room group" and `room_index`.
- Python: one class per file, file in snake case (`brnz_record_journal_entries.py`, `reader_csv.py`), classes `<Prefix>Record<Dataset>` (`BrnzRecordJournalEntries`), `<Format>Reader` (`CSVReader`). There is one `Loader`, the same for every layer and every reader. Test files are `test_<module>.py`, with a name that is unique across `tests/unit` and `tests/integration`.
- Meta tables are the exception to the layer prefix: `meta_<layer>` with the full layer word (`dev_bronze.meta_bronze`), one per layer for every dataset of the layer. Their row model is `MetaRecord`, without a layer prefix or a dataset, because it is the same for every meta table. Bronze and corrections have no `meta_` columns: their metadata is in `meta_bronze` and `meta_corrections`, and every `kind` starts with `meta_` (`meta_source`, `meta_reviewed_by`), the name the fact would have as a column. Only these two inputs have a meta table; the layers built by dbt have none.
- Snapshots are the other exception: `snap_<recorded table>`, the full name of the one table it records (`snap_corr_journal_entries`, `snap_meta_corrections`, `snap_slvr_journal_entries`). A snapshot mirrors that table exactly, with no join, filter or derived column; anything combined from several snapshots is a view on top of them. Its `unique_key` is the primary key of the recorded table, its strategy is `check` on all columns, `hard_deletes` is `new_record`. dbt's columns are renamed to `meta_valid_from`, `meta_valid_to` (null on the current version), `meta_version_id`, `meta_updated_at` and `meta_is_deleted`. A snapshot is kept only for a table whose rows can change, so bronze and `meta_bronze`, which are append-only, have none.
- Unique key index: `uq_<table>_key` (`uq_brnz_journal_entries_key`).

## SQL style

- The column order of a select is deliberate (it matches the corrections table and the Excel upload) and must not be rearranged.
- dbt models: a chain of CTEs named with a verb (`identify_room_index`, `assign_position`), each doing one thing, with a lowercase `--` comment saying why. The final select lists columns explicitly so helper columns are not exposed.
- Do not repeat logic across CTEs: compute a value once and reuse it.
- Repeated column lists go in a Jinja `{% set %}` list and a loop.
- `Database/*.sql` (hand-written DDL): uppercase keywords, `CREATE ... IF NOT EXISTS`. These scripts are not formatted by any tool.

## Python style

- Comments are lowercase `# ` lines above the code they explain.
- Every row model inherits `Record` (`extra="forbid"`, empty string becomes `None`, a pandas NaN is refused). `Record` has no fields; each model declares its own. The metadata of a row is not a field: `BrnzRecord` and `CorrRecord` carry it as `meta_records`, excluded from `model_dump`.
- Turning missing values into `None` is the reader's job, not the model's. A dataframe from CSV and one from Excel must look the same where cells are empty.
- A row model mirrors its SQL table as closely as possible: same column names, order, lengths and nullability.
- Database errors are caught per exception type, printed with context, and re-raised. Loads run in one transaction.
