# CLAUDE.md
A bronze/silver/gold data warehouse. Bad data never reaches silver: a load that fails its data tests is refused, and the file is fixed where it came from. Bronze is append-only, so a refused load stays there as a record of what arrived. Gold is where the data modeling happens.

## How to work
- One step at a time: make the change that was asked, report, and wait. Large multi-file changes in one go are not wanted.
- Files outside the repo are read only. Ask permission when one needs to change.

## Environment
- Windows tooling is minimal: most of the work happens inside docker containers.
- Usual setup: one window, the dev container (`.devcontainer/dev`), with Claude Code running inside it. Every tool (`dbt`, `meltano`, `python`, `ruff`, `sqlfmt`, `pytest`) is on `PATH` and works from any folder. There is no Docker inside: commands that need Docker are for the user to run on Windows. How the images are cut, dev and prod kept apart, the volumes and the dev container: `docs/DEV_CONTAINER.md`.
- A library goes into its requirements file, never installed by hand (`pip install` in the dev container terminal): `docker/<image>/requirements-<venv>.txt`, one file per venv, named after it: `requirements-airflow.txt`, `-dbt`, `-meltano` in `docker/pipeline/`, `requirements-webapps.txt` and `requirements-datastreamer.txt` in their image's folder, and for a dev tool `docker/pipeline/requirements-tools.txt` (or `requirements-pytest.txt`).
- Only when working from Windows: in PowerShell, `psql -c` loses double quotes, so `"DataWarehouse"` arrives unquoted and fail or hit the wrong object. Run such statements through the Bash tool. In Bash, a container path (`--workdir /usr/app`) needs `MSYS_NO_PATHCONV=1` in front of the docker command.
- Running compose from Windows after a Dev Container was opened (or the other way round) can recreate the postgres container, because the two write the repo path as `C:\` and `c:\`. The data stays in the volume, but open connections (Excel, VS Code SQL tabs) drop. `--no-deps` avoids it for commands that do not need the database.

## Database and dbt
- On `dev` or a `feature-*` or `hotfix-*` branch, in a dev container, any command that affects the database is allowed. On `main` or in the prod stack, the database is not touched in any way.
- Use `dbt build`, not `dbt run`: dbt-postgres replaces a view by dropping the old one with `CASCADE`, so rebuilding a view alone silently drops every view on top of it.
- A package added to `packages.yml` means updating `package-lock.yml` too.
- A load is one dataset, one run of the Airflow DAG `load_<dataset>` (`DataWarehouseAirflow/dags/load_datasets.py`), started by hand: `no_open_load`, `ingest` (`meltano run tap-csv-<dataset> target-postgres`, with a new uuidv7 in `MELTANO_RUN_ID`, which every bronze row gets as `load_id`), `audit` (`stg_<dataset>` and its data tests), `publish` (`slvr_<dataset>+`, in the `publish` pool of one slot). The dbt steps are Cosmos task groups, one task per dbt node, drawn from the dbt manifest (`utils/dbt_task_group.py`). Each extractor inherits from `tap-csv`, which is never run itself.
- A load's state is one row in `dw_control.ctl_loads`, written only by the DAG: `landed`, then `accepted` or `refused`, then `published` or `failed`. dbt reads it, so there is no `load_id` var: staging holds the open load (`landed` or `accepted`), so its data tests judge it alone and a file without rows is refused; silver takes it only once it is `accepted` (`macros/select_accepted_loads.sql`), and a row replaces the one with the same `unique_key`, with a warning. Every run ends its load; a load left open by an outage stops the next run until a person ends it in `ctl_loads`. Failing rows are in Elementary's tables (`dw_elementary`), by `row_id`.
- What dbt writes lives in the `dbt-state` volume, dev and prod alike, one folder per role, each its own target and logs (`x-dbt-env` in `docker/compose.yaml`): in `/dbt-state/<RELEASE>/` (dev's release is `dev`), `airflow-manifest` (Airflow's manifest, which the DAGs are drawn from, written only by `airflow-init` on every `up`), `setup-build`, and `interactive` (any command that names no target: yours, dbt Power User's); and `/dbt-state/metadata-export` (`refresh_metadata`, for OpenMetadata and the ERD), shared by the releases. A script or DAG that runs dbt names its own target. A new or changed model or test reaches the load DAGs only when Airflow's manifest is refreshed: an `up`, or in the dev container `dbt parse --target-path $DBT_STATE_DIR/airflow-manifest/target --log-path $DBT_STATE_DIR/airflow-manifest/logs`. Never while a load runs, nor an `up`: it would change the DAG under the load.
- A new database needs the DDL, then the setup build, then the first loads, in any order. The setup build is every model, the seeds and Elementary's tables, without the data tests declared in staging's yml, which judge a load: with no load open, staging is empty, so silver and gold are created empty and every relation exists before the first load. The setup scripts (`docker/02_setup_dev.ps1`, `docker/03_setup_prod.ps1`) end with it: `dbt build --selector setup` (`DataWarehouseDbt/selectors.yml`), one dbt process, so each schema is created once. Run the script again after a seed or a model changes, never while a load runs; in the dev container, `dbt build --selector setup` alone does the same.
- Gold's keys exist only for its readers (OpenMetadata, Excel, Power BI): nothing in the pipeline relies on them. dbt_constraints is off in every dbt run (`dbt_constraints_enabled` in `dbt_project.yml`), and a table built again loses its keys. The DAG `refresh_metadata`, started by hand before an OpenMetadata ingestion or a new Excel or Power BI model, runs every key test with the package on, and adds back every missing key whose test passes.

## Data rules
- `row_id` is the primary key of bronze and the only column shared between datasets, carried unchanged through the pipeline. Silver has no constraints, only an index on its business key. In gold a fact's primary key is its business key, `row_id` is a unique key, and every key is a dbt_constraints test (`docs/CODING_STANDARDS.md`).
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
