# CLAUDE.md
A bronze/silver/gold data warehouse. Bad data never reaches silver, and a human fixes it without touching the source file or bronze. Gold is where the data modeling happens.

## How to work
- One step at a time: make the change that was asked, report, and wait. Large multi-file changes in one go are not wanted.
- Files outside the repo are read only. Ask permission when one needs to change.

## Environment
- Windows tooling is minimal: most of the work happens inside docker containers.
- Usual setup: Window 1 is Claude Code, with an overview of the whole repo; Window 2 is a Dev Container opened on the relevant container.
- A library goes into the Dockerfile, never installed by hand (`pip install` in the dev container terminal).
- In PowerShell, `psql -c` loses double quotes, so `"DataWarehouse"` or `"position"` arrive unquoted and fail or hit the wrong object. Run such statements through the Bash tool.
- Running compose from Windows after a Dev Container was opened (or the other way round) can recreate the postgres container, because the two write the repo path as `C:\` and `c:\`. The data stays in the volume, but open connections (Excel, VS Code SQL tabs) drop. `--no-deps` avoids it for commands that do not need the database.

## Database and dbt
- On `dev` or a hotfix branch, in a dev container, any command that affects the database is allowed. On `prod` or in the prod stack, the database is not touched in any way.
- Use `dbt build`, not `dbt run`: dbt-postgres replaces a view by dropping the old one with `CASCADE`, so rebuilding a view alone silently drops every view on top of it.
- A package added to `packages.yml` means updating `package-lock.yml` too.
- A full loop is: DDL, `load_bronze()`, `dbt build` (tests fail, silver skipped), review in the web app, whose submit runs `dbt build` (silver built).

## Data rules
- `row_id` is the primary key and the only column shared between datasets, carried unchanged through the pipeline.
- A datetime is text up to silver, with its time zone written from staging on: the source's, or the `timezone` var (`Europe/Amsterdam`, from `TZ` in `docker/compose.yaml`) appended by staging when the source wrote none. The castable test accepts only a zone that cannot be misread (`macros/aud_castable.sql`); silver casts it to `timestamptz(0)`, rounded to the second. A metadata date-time is written with its offset (`2026-10-22T14:42:08+02:00`). A date without a zone is assumed `Europe/Amsterdam`: warn every time this assumption is not true.
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
One context: `GLOSSARY-MAP.md` at the repo root points to `docs/GLOSSARY.md`, which holds the domain modeling names (skill: `/mattpocock-skills:domain-modeling`). The glossary lives only where `GLOSSARY-MAP.md` says, never as a root `GLOSSARY.md`. There are no ADRs; a new one goes in `docs/adr/`. See `docs/agents/domain.md`.
