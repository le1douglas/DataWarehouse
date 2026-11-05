# CLAUDE.md
A bronze/silver/gold data warehouse. Bad data never reaches silver: a load that fails its data tests is refused, and the file is fixed where it came from. Bronze is append-only, so a refused load stays there as a record of what arrived. Gold is where the data modeling happens.

## How to work
- One step at a time: make the change that was asked, report, and wait. Large multi-file changes in one go are not wanted.
- Files outside the repo are read only. Ask permission when one needs to change.

## Environment
- Windows tooling is minimal: most of the work happens inside docker containers.
- Usual setup: Window 1 is Claude Code, with an overview of the whole repo; Window 2 is a Dev Container opened on the relevant container.
- A library goes into the Dockerfile, never installed by hand (`pip install` in the dev container terminal).
- In PowerShell, `psql -c` loses double quotes, so `"DataWarehouse"` arrives unquoted and fail or hit the wrong object. Run such statements through the Bash tool. In Bash, a container path (`--workdir /usr/app`) needs `MSYS_NO_PATHCONV=1` in front of the docker command.
- Running compose from Windows after a Dev Container was opened (or the other way round) can recreate the postgres container, because the two write the repo path as `C:\` and `c:\`. The data stays in the volume, but open connections (Excel, VS Code SQL tabs) drop. `--no-deps` avoids it for commands that do not need the database.

## Database and dbt
- On `dev` or a hotfix branch, in a dev container, any command that affects the database is allowed. On `prod` or in the prod stack, the database is not touched in any way.
- Use `dbt build`, not `dbt run`: dbt-postgres replaces a view by dropping the old one with `CASCADE`, so rebuilding a view alone silently drops every view on top of it.
- A package added to `packages.yml` means updating `package-lock.yml` too.
- A load is two commands, until an orchestrator runs them: `meltano run tap-csv target-postgres` with a new uuidv7 (`select uuidv7()`) in `MELTANO_RUN_ID`, which every bronze row gets as `load_id`, then `dbt build --select source:dw_bronze.<table>+ --vars "{load_id: <the same id>}"`. Staging holds only that load, so its data tests judge it alone, and a file without rows is refused. Without the var, a build that compiles staging fails on purpose. Silver adds it only when they pass, and a row replaces the one with the same `unique_key`, with a warning.
- A new database needs the DDL, then one whole `dbt build` without the var, then the first load and its build. The whole build makes what a load's selection leaves out (seeds, dims, Elementary's tables, `aud_issues`); it fails the row-count test and skips silver, as expected. Without it the first load's build errors on the missing dims, and nothing reaches `aud_issues`.

## Data rules
- `row_id` is the primary key and the only column shared between datasets, carried unchanged through the pipeline.
- A datetime is text up to staging, which appends the `timezone` var (`Europe/Amsterdam`, from `TZ` in `docker/compose.yaml`) and casts it to `timestamptz(0)`, rounded to the second. The cast accepts only a zone that cannot be misread (`macros/cast_select.sql`). A date without a zone is assumed `Europe/Amsterdam`: warn every time this assumption is not true.
- Empty string means null. The decimal separator is `.`.

## Agent skills

### Coding standards
`docs/CODING_STANDARDS.md` holds the naming conventions and the programming style guide.

### NiceGUI standards
`docs/NICEGUI_STANDARDS.md` holds the rules for the NiceGUI interface. The full NiceGUI documentation is one JSON file, https://nicegui.io/static/sitewide_index.json: look an API up there, do not guess it.

### Git standards
`docs/GIT_STANDARDS.md` holds the branches (`dev`, `prod`), releases, hotfixes and commit messages.

### Issue tracker
Issues and specs live as markdown files under `.scratch/<feature-slug>/` in this repo. See `docs/agents/issue-tracker.md`.

### Domain docs
One context: `GLOSSARY-MAP.md` at the repo root points to `docs/GLOSSARY.md`, which holds the domain modeling names (skill: `/mattpocock-skills:domain-modeling`). The glossary lives only where `GLOSSARY-MAP.md` says, never as a root `GLOSSARY.md`. ADRs are in `docs/adr/`. See `docs/agents/domain.md`.
