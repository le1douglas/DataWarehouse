# CLAUDE.md
A bronze/silver/gold data warehouse. Bad data never reaches silver: a load that fails its data tests is refused, and the file is fixed where it came from. Bronze is append-only, so a refused load stays there as a record of what arrived. Gold is where the data modeling happens.

## How to work
- One step at a time: make the change that was asked, report, and wait. Large multi-file changes in one go are not wanted.
- Files outside the repo are read only. Ask permission when one needs to change.

## Environment
- Windows tooling is minimal: most of the work happens inside docker containers.
- Usual setup: one window, the dev container (`.devcontainer/dev`), with Claude Code running inside it. Every tool (`dbt`, `meltano`, `python`, `ruff`, `sqlfmt`, `pytest`) is on `PATH` and works from any folder. There is no Docker inside: commands that need Docker are for the user to run on Windows. Core, dev and prod images and volumes: `docs/DEV_CONTAINER.md`.
- A library goes into its requirements file, never installed by hand (`pip install` in the dev container terminal): `docker/<image>/requirements.txt` for an image, `docker/dev/requirements.txt` (or `requirements-test.txt`) for a dev tool.
- Only when working from Windows: in PowerShell, `psql -c` loses double quotes, so `"DataWarehouse"` arrives unquoted and fail or hit the wrong object. Run such statements through the Bash tool. In Bash, a container path (`--workdir /usr/app`) needs `MSYS_NO_PATHCONV=1` in front of the docker command.
- Running compose from Windows after a Dev Container was opened (or the other way round) can recreate the postgres container, because the two write the repo path as `C:\` and `c:\`. The data stays in the volume, but open connections (Excel, VS Code SQL tabs) drop. `--no-deps` avoids it for commands that do not need the database.

## Database and dbt
- On `dev` or a `feature-*` or `hotfix-*` branch, in a dev container, any command that affects the database is allowed. On `main` or in the prod stack, the database is not touched in any way.
- Use `dbt build`, not `dbt run`: dbt-postgres replaces a view by dropping the old one with `CASCADE`, so rebuilding a view alone silently drops every view on top of it.
- A package added to `packages.yml` means updating `package-lock.yml` too.
- A load is two commands, until an orchestrator runs them: `meltano run tap-csv target-postgres` with a new uuidv7 (`select uuidv7()`) in `MELTANO_RUN_ID`, which every bronze row gets as `load_id`, then `dbt build --select source:dw_bronze.<table>+ --vars "{load_id: <the same id>}"`. Staging holds only that load, so its data tests judge it alone, and a file without rows is refused. Without the var, a build that compiles staging fails on purpose. Silver adds it only when they pass, and a row replaces the one with the same `unique_key`, with a warning.
- A new database needs the DDL, then one whole `dbt build` without the var, then the first load and its build. The whole build makes what a load's selection leaves out (seeds, `ref_` models, dims, Elementary's tables, `aud_issues`); it fails the row-count test and skips silver, as expected. Without it the first load's build errors on the missing dims, and nothing reaches `aud_issues`.

## Data rules
- `row_id` is the primary key up to silver and the only column shared between datasets, carried unchanged through the pipeline. In gold a fact's primary key is its business key, and `row_id` is a unique key. Every key of a dbt model is a dbt_constraints test (`docs/CODING_STANDARDS.md`).
- A datetime is text up to staging, which appends the `timezone` var (`Europe/Amsterdam`, from `TZ` in `docker/compose.yaml`) and casts it to `timestamptz`, to the microsecond. The cast accepts only a zone that cannot be misread (`macros/cast_select.sql`). A date without a zone is assumed `Europe/Amsterdam`: warn every time this assumption is not true.
- Empty string means null. The decimal separator is `.`.
- Silver keeps the precision the source sends. Gold reduces it per dataset: for journal entries, `date_time` truncated to the second and decimals rounded to `numeric(4,2)`.

## Agent skills

### Coding standards
`docs/CODING_STANDARDS.md` holds the naming conventions and the programming style guide.

### NiceGUI standards
`docs/NICEGUI_STANDARDS.md` holds the rules for the NiceGUI interface. The full NiceGUI documentation is one JSON file, https://nicegui.io/static/sitewide_index.json: look an API up there, do not guess it.

### Git standards
`docs/GIT_STANDARDS.md` holds the branches (`main`, `dev`, `feature-*`, `hotfix-*`), the actions that move changes between them (features, releases, hotfixes) and the guardrails (git config, hooks, GitHub rulesets).

### Issue tracker
Issues and specs live as markdown files under `.scratch/<feature-slug>/` in this repo.

### Domain docs
One context: `docs/GLOSSARY.md` holds the domain modeling names. The glossary lives only there, never as a root `GLOSSARY.md`.
