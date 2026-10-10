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

- A prefix never contains an underscore: the prefix ends at the first `_`, the detail starts at `__`. Prefixes do not need the same length.
- Tables and dbt models: `<prefix>_<dataset>` (`dev_bronze.brnz_journal_entries`, `slvr_journal_entries`). The dbt file name is the relation name; no `alias` and no `generate_alias_name` or `generate_schema_name` override. The folder decides materialisation and schema in `dbt_project.yml`.
- dbt sources are named after the schema and the table: `source("dev_bronze", "brnz_journal_entries")`.
- dbt singular tests: `aud_<dataset>__<rule>.sql`, each with `{{ config(severity='error', store_failures=true) }}`, pointing at the candidate model. The file name is the name of the failure table in `dev_audit`, and relation names are limited to 63 characters.
- A data test returns whole, unchanged candidate rows: `select * from {{ ref("cand_<dataset>") }} where ...`, on one candidate model, with no column added, removed or changed. The audit view depends on it: a data test that does otherwise still runs and still fails the build, but it is left out of the view with a warning.
- Audit view: `aud_<dataset>` (`dev_audit.aud_journal_entries`), one per candidate model, next to the failure tables `aud_<dataset>__<rule>`. It is created by the `create_audit_views` macro after every run, not by a model, and its `meta_failed_tests` column holds the `<rule>` part of each data test the row failed.
- Metadata columns start with `meta_` (`meta_extract_date_time`, `meta_source`, `meta_cast_errors`, `meta_is_corrected`, `meta_reviewed_by`, `meta_reviewed_date_time`, `meta_failed_tests`, `meta_silver_date_time`). The Excel side filters on this prefix, so a non-`meta_` column in staging is treated as correctable.
- From staging onwards the bronze column `tags` is called `room`. Names and comments use "room", "room group" and `room_index`.
- Python: one class per file, file in snake case (`brnz_record_journal_entries.py`, `reader_csv.py`), classes `<Prefix>Record<Dataset>` (`BrnzRecordJournalEntries`), `<Prefix>Loader` (`CorrLoader`), `<Format>Reader`. Test files are `test_<module>.py`, with a name that is unique across `tests/unit` and `tests/integration`.
- Unique key index: `uq_<table>_key` (`uq_brnz_journal_entries_key`).

## SQL style

- The column order of a select is deliberate (it matches the corrections table and the Excel upload) and must not be rearranged.
- dbt models: a chain of CTEs named with a verb (`identify_room_index`, `assign_position`), each doing one thing, with a lowercase `--` comment saying why. The final select lists columns explicitly so helper columns are not exposed.
- Do not repeat logic across CTEs: compute a value once and reuse it.
- Repeated column lists go in a Jinja `{% set %}` list and a loop.
- `Database/*.sql` (hand-written DDL): uppercase keywords, `CREATE ... IF NOT EXISTS`. These scripts are not formatted by any tool.

## Python style

- Comments are lowercase `# ` lines above the code they explain.
- Every row model inherits `Record` (`extra="forbid"`, empty string becomes `None`, a pandas NaN is refused). `Record` has no fields; each model declares its own, including the `meta_` ones.
- Turning missing values into `None` is the reader's job, not the model's. A dataframe from CSV and one from Excel must look the same where cells are empty.
- A row model mirrors its SQL table as closely as possible: same column names, order, lengths and nullability.
- Database errors are caught per exception type, printed with context, and re-raised. Loads run in one transaction.
