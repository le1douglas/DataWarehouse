# CLAUDE.md
- we are buyilding a A bronze/silver/gold data warehouse. The design goal is that bad data never reaches silver, and that a human can fix it without touching the source file or bronze. gold is where the data modeling happens.
- Go one step at a time. Make the change that was asked, report, and wait. Large multi-file changes in one go are not wanted.
- Do not run `dbt build` or anything
- files oustise the repo should be read only. if nedded, ask for permission
- `docs/CODING_STANDARDS.md` hold the naming conventions and the programming style guide
- `docs/GLOSSARY.md` hold domain modeling names, related to it, there is the /mattpocock-skills:domain-modeling skill
- `docs/DATA_FLOW_DIAGRAM.md` The diagram of the pipeline. Update it when an object or a dependency between objects changes.
- windows tooling is minimal, most of the work happens inside docker containers
- the usual work setup is
    - Window 1: where calude code lives, with an oveeview of the whole repo
    - Window 2: a Dev container opened on the relevant container
- Bronze stores everything as text, exactly as received.
- `row_id` is the only column shared between datasets, and is the primary key. is carried unchanged through the data pipeline
- Datetimes have no time zone anywhere before silver, and are cut to the second. Silver is the only place a zone is assigned, from the `timezone` var (`Europe/Amsterdam`). dates are aussmed to be `Europe/Amsterdam` when not specified. Warn every time this assuption is not true
- Empty string means null. The decimal separator is `.`
- In PowerShell, `psql -c` loses double quotes, so `"DataWarehouse"` or `"position"` arrive unquoted and fail or hit the wrong object. Run such statements through the Bash tool instead.

Running compose from Windows after a Dev Container was opened (or the other way round) can recreate the postgres container, because the two write the repo path as `C:\` and `c:\`. The data stays in the volume, but open connections (Excel, VS Code SQL tabs) drop. `--no-deps` avoids it for commands that do not need the database.

dbt-postgres replaces a view by dropping the old one with `CASCADE`, so rebuilding a view alone drops every view on top of it without a warning: `dbt run --select stg_journal_entries` drops `cand_journal_entries`, and the tests then error with "relation does not exist". Select the views downstream too (`--select stg_journal_entries+`, but that also builds silver without its tests, so prefer `dbt build`), or recreate them after with `dbt run --select cand_journal_entries`. Silver is a table and is not affected.

A full loop is: DDL, `load_bronze()`, `dbt build` (tests fail, silver skipped), review in Excel, `load_corrections()`, `dbt build` (silver built). Machine setup (Docker, the env files, ODBC) is documented step by step in `docs/DOCKER_IMPLEMENTATION.md`.

## Agent skills

### Issue tracker

Issues and specs live as markdown files under `.scratch/<feature-slug>/` in this repo. See `docs/agents/issue-tracker.md`.

### Domain docs

One context: `GLOSSARY-MAP.md` at the repo root points to `docs/GLOSSARY.md`. There are no ADRs; a new one goes in `docs/adr/`. See `docs/agents/domain.md`.
Do not create a `GLOSSARY.md` in the repo root, instead follow the instructions in `GLOSSARY-MAP.md`.
