# Installation guide (Docker)

From a new Windows 11 PC to a running dev and prod stack, with Excel and VS Code connected to both.

- Follow the sections in order.
- Run every command in PowerShell, **from the repo root**, unless said otherwise.
- Every dev command passes both compose files: `docker compose -f docker/compose.yaml -f docker/compose.dev.yaml ...`.
- Needed: administrator rights (Docker Desktop, ODBC driver), a GitHub account with access to the repo.

---

## 1. Install the Windows tools

### Docker Desktop

- Task Manager → **Performance** → **CPU** → **Virtualization** must say **Enabled**
  - If Disabled: enable Intel VT-x / AMD-V in the BIOS/UEFI first
- `wsl --update`, then `wsl --version` (expect `WSL version: ...`)
- Download [Docker Desktop](https://www.docker.com/products/docker-desktop/) → **Download for Windows – AMD64**
- In the installer:
  - **Install for all users** (the per-user install fails)
  - **Use WSL 2 instead of Hyper-V** ticked
- Restart the PC
- Open Docker Desktop: accept, skip sign-in, skip the survey
- **Settings** → **General** → tick **Start Docker Desktop when you sign in to your computer** → **Apply**
- Check, in a new PowerShell: `docker version` (expect a `Client:` and a `Server: Docker Desktop` block)

### Git

- [Download](https://git-scm.com/install/windows), installer defaults, except:
  - **Initial branch name:** the default (it only names the branch of a new repository; a clone of this one starts
    on `dev`)
  - **Credential helper:** Git Credential Manager
- `git config --global user.name "Your Name"`
- `git config --global user.email "you@example.com"`

### VS Code

- [Download](https://code.visualstudio.com/), tick **Add to PATH** and the **Open with Code** context menu entries
- `git config --global core.editor "code --wait"`
- Extensions (`Ctrl + Shift + X`):
  - **Dev Containers** (Microsoft)
  - **Container Tools** (Microsoft), optional: containers and images in the sidebar
  - **PostgreSQL** (Microsoft)
- The Python, ruff, dbt Power User and Claude Code extensions are **not** installed on Windows: the dev container
  installs them

### psqlODBC (for Excel)

- Download the 64-bit `.msi` from [odbc.postgresql.org](https://odbc.postgresql.org) (Downloads → MSI) and install it
- No PostgreSQL server on Windows: the database runs in Docker

---

## 2. Get the repo

- `cd` into the parent folder, then:
  - `git clone https://github.com/le1douglas/DataWarehouse.git`
  - `cd DataWarehouse`
- If the repo is inside OneDrive: right-click the repo folder → **Always keep on this device**
  - A cloud-only file is empty for a container (CSV, env files)

---

## 3. Env files: `01_setup_env.ps1`

- `powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1`
  - Writes the two env files in `docker/`: `.env` and `.env.prod`
  - Asks a password for dev, then for prod: no spaces, quotes, `$` or `#`
  - `RELEASE` in `.env.prod` is the newest git tag at that moment
  - Existing files: answer `N` to keep them and create only the missing ones

### Check

- `git status --short --ignored docker` → both listed with `!!`
- `Select-String -Path docker\.env.prod -Pattern '^RELEASE='` → the newest tag (`git tag --sort=-creatordate`, first line)

---

## 4. Dev stack: `02_setup_dev.ps1`

- `powershell -ExecutionPolicy Bypass -File docker\02_setup_dev.ps1`
  - Builds the `pipeline`, `webapps` and `dev` images, starts postgres, creates the `airflow` database when it is
    missing, starts Airflow and the web app, runs `meltano install` and `dbt debug` in the Airflow scheduler, and ends
    with the setup build. `airflow-init`, started by `up` before the other Airflow components, installs the dbt packages
    and refreshes Airflow's manifest, which the DAGs are drawn from
    (`DataWarehouseAirflow/dags/utils/dbt_task_group.py`), into `/dbt-state/dev/airflow-manifest` (see
    **Daily workflow**)
  - First run takes a few minutes; safe to run again; stops at the first failing step
  - Ends with `dev setup done`

### Check

- Docker Desktop → **Containers** → group `dw-dev` → `dw-dev-postgres-1`, `dw-dev-airflow-api-server-1`,
  `dw-dev-airflow-scheduler-1`, `dw-dev-airflow-dag-processor-1` running, `dw-dev-airflow-init-1` exited
- Airflow UI at `http://localhost:8090` (`AIRFLOW_PORT` in `docker/.env`), no login: the DAGs
  `refresh_metadata`, `load_journal_entries` and `load_plants_batches`, and **Admin** → **Pools** → `publish` with 1 slot
- `docker exec dw-dev-postgres-1 psql -U postgres -d DataWarehouse -c "SHOW timezone;"` → `Europe/Amsterdam`
- `docker exec dw-dev-postgres-1 psql -U postgres -d DataWarehouse -c "SELECT now();"` → Amsterdam offset (`+01`
  winter, `+02` summer)
- `docker exec dw-dev-postgres-1 psql -U postgres -d DataWarehouse -c "\dt dw_*.*"` → `brnz_journal_entries`,
  `brnz_plants_batches` and `ctl_loads`
- `docker exec dw-dev-postgres-1 psql -U postgres -l` → `DataWarehouse`, `airflow` and `meltano`
- `docker exec dw-dev-postgres-1 psql -U postgres -d meltano -c "\dt"` → `alembic_version`, `plugin_settings`, `runs`,
  `state`: Meltano's own tables, created by `meltano install`
- `docker image ls` → `pipeline`, `webapps` and `dev`, tag `dev`
- `docker volume ls` → `dw-dev_pgdata`, `dw-dev_meltano-plugins`, `dw-dev_dbt-state` (what dbt writes, and dev's
  dbt packages, not in the repo folder), `dw-dev_airflow-logs`
- `docker exec dw-dev-airflow-scheduler-1 ls /dbt-state /dbt-state/dev` → `dev` (and `metadata-export` once
  `refresh_metadata` has run); `airflow-manifest`, `interactive`, `packages`, `setup-build`
- `docker exec dw-dev-postgres-1 psql -U postgres -d DataWarehouse -c "\dn dw_*"` → `dw_bronze`, `dw_control`,
  `dw_elementary`, `dw_gold`, `dw_seeds` and `dw_silver`: the script's last step, `dbt build --selector setup`, built
  the seeds, every model (silver and gold empty) and Elementary's tables. The database is ready for its first loads,
  in any order

---

## 5. Prod stack: `03_setup_prod.ps1`

- No uncommitted changes (commit or stash first): the build switches the repo to the tag
- `powershell -ExecutionPolicy Bypass -File docker\03_setup_prod.ps1`
  - Builds the `pipeline`, `webapps` and `datastreamer` images of `RELEASE` from the tag's code, then switches the
    repo back. The `pipeline` image holds dbt, Meltano, their projects and the dbt packages; its build runs
    `dbt parse` to check the project
  - Images of `RELEASE` that exist are not rebuilt
  - Starts postgres, creates the `airflow` database when it is missing, starts Airflow and the web app (`airflow-init`
    refreshes Airflow's manifest into `/dbt-state/<RELEASE>/airflow-manifest` of `dw-prod_dbt-state`), runs `dbt debug`
    in the Airflow scheduler, and ends with the setup build
  - Safe to run again; stops at the first failing step
  - Ends with `prod setup done, on <RELEASE>`

### Check

- Docker Desktop → **Containers** → group `dw-prod` → `dw-prod-postgres-1` running
- `docker exec dw-prod-postgres-1 psql -U postgres -d DataWarehouse -c "SHOW timezone;"` → `Europe/Amsterdam`
- `docker exec dw-prod-postgres-1 psql -U postgres -d DataWarehouse -c "\dt dw_*.*"` → the same tables as dev
- `docker exec dw-prod-postgres-1 psql -U postgres -l` → `DataWarehouse`, `airflow` and `meltano`
- `docker image ls` → `pipeline`, `webapps` and `datastreamer`, tag = `RELEASE`
- Airflow UI at `http://localhost:8091` (`AIRFLOW_PORT` in `docker/.env.prod`)
- `docker compose -f docker/compose.yaml -f docker/compose.prod.yaml --env-file docker/.env.prod exec airflow-scheduler dbt debug`
  → `All checks passed!`

---

## 6. Excel

### ODBC data sources

Start → **ODBC Data Sources (64-bit)** → **System DSN** → **Add** → `PostgreSQL Unicode(x64)`, one per environment:

| Field | Dev | Prod |
|---|---|---|
| Data source name | `PostgreSQL_DataWarehouse` | `PostgreSQL_DataWarehouse_Prod` |
| Database | `DataWarehouse` | `DataWarehouse` |
| Server | `localhost` | `localhost` |
| User Name | `postgres` | `postgres` |
| SSL Mode | `disable` | `disable` |
| Port | `5432` | `5433` |
| Password | from `docker/.env` | from `docker/.env.prod` |

- **Test** → **Connection successful** → **Save**
- Excel reads the database through these data sources
  - Asked for credentials: **Database** → user `postgres` and the password → **Connect**
  - Change them later: **Data** → **Get Data** → **Data Source Settings**

---

## 7. VS Code

### Database connections

- PostgreSQL sidebar → **Add connection**, one per environment:
  - **Host:** `localhost`, **Database:** `DataWarehouse`, **User:** `postgres`
  - **Port:** `5432` (dev) / `5433` (prod)
  - **Password:** `POSTGRES_PASSWORD` of `docker/.env` (dev) / `docker/.env.prod` (prod)
- Check: right-click → **New Query** → `SELECT version();` → `PostgreSQL 18.x (Debian ...)`
- Meltano's own database, `meltano`, is on the same server: the same connection with **Database:** `meltano`, if the
  sidebar does not list it next to `DataWarehouse`

### The dev container

- `code .` from the repo root
- `Ctrl + Shift + P` → **Dev Containers: Reopen in Container**
  - One container, `dev`, with every tool: `dbt`, `meltano`, `python`, `ruff`, `sqlfluff`, `pytest`, from any folder
  - First open installs the extensions and Claude Code in the container
  - Claude Code: sign in once. Its login, settings and memory are kept in the `dw-dev_claude-config` volume
  - `meltano.yml` gets completion and validation from Meltano's schema (YAML extension)
  - Back to Windows: **Dev Containers: Reopen Folder Locally**
- What is where, and how to move Claude's volume to another machine: `docs/DEV_CONTAINER.md`

Setup is done.

---

## Daily workflow

### The loop

- Each step runs either from PowerShell (repo root) or in the VS Code terminal of the dev container (opens at `/usr/app`)
- Stick to one of the two in a session: switching recreates postgres and drops Excel's connection (see pitfalls)
- Prod: the same PowerShell commands with `-f docker/compose.prod.yaml --env-file docker/.env.prod` instead of
  `-f docker/compose.dev.yaml`, and the web app on port 8081

**Set up the warehouse**

- A new database is set up by the setup script (`02_setup_dev.ps1`, `03_setup_prod.ps1`): its last step,
  `dbt build --selector setup`, builds every relation: the seeds, every model and Elementary's tables, without the
  data tests of a load (those declared in staging's yml). With no load open, staging is empty, so silver and gold are
  created empty, and the first loads run in any order
- After a seed or a model changes: run the setup script again. In the dev container, `dbt build --selector setup`
  alone does the same. It adds nothing to silver, and rebuilds gold from it, so the facts take a changed seed at once
- Never while a load runs: it builds staging, silver and gold, as a load does
- Before an OpenMetadata ingestion, or before a new Excel or Power BI model: trigger the DAG `refresh_metadata`. It
  adds gold's primary, unique and foreign keys, which these tools read and a build of gold drops. A key whose table
  is not built yet fails the run, after the others are added. It writes to `/dbt-state/metadata-export`

**Refresh Airflow's manifest**

- The load DAGs are drawn from Airflow's manifest, in `/dbt-state/<RELEASE>/airflow-manifest` of the `dbt-state`
  volume, not from the dbt project: a new, renamed or removed model or test reaches them only when it is refreshed
- Refreshed by `airflow-init` on every `up`, so by `02_setup_dev.ps1` and `03_setup_prod.ps1` too. In the dev
  container, without an `up`:
  `dbt parse --target-path $DBT_STATE_DIR/airflow-manifest/target --log-path $DBT_STATE_DIR/airflow-manifest/logs`
- Never while a load runs, and no `up` while a load runs: it would change the DAG under the load. No other dbt
  command writes it: your commands and dbt Power User write to `interactive`, the setup build to `setup-build`
- The ERD of the dev container (dbterd) reads `/dbt-state/metadata-export`. To draw the current project:
  `dbt docs generate --target-path $DBT_METADATA_EXPORT_DIR/target --log-path $DBT_METADATA_EXPORT_DIR/logs`
- Each prod release has its own folder, `/dbt-state/<RELEASE>`, so a rollback finds its manifest unchanged. Old ones
  are not removed by anything: once a release is not coming back,
  `docker compose -f docker/compose.yaml -f docker/compose.prod.yaml --env-file docker/.env.prod exec airflow-scheduler rm -r /dbt-state/<old RELEASE>`

**Load a file**

- A load is one dataset, one run of its DAG, `load_<dataset>`, started by hand in the Airflow UI (dev
  `http://localhost:8090`, prod `http://localhost:8091`): the DAG → **Trigger**. A new DAG starts paused: unpause it
  first. From the dev container, `airflow dags trigger load_<dataset>` does the same
- Each dataset has its own file in `USER_INPUT_DIR` (`docker/.env`), its own extractor in
  `DataWarehouseMeltano/meltano.yml` and its own bronze table. Dev and prod read the same folder:

  | Dataset | DAG | File | Extractor | Bronze table |
  | --- | --- | --- | --- | --- |
  | Journal entries | `load_journal_entries` | `journal_entries/journal_entries.csv` | `tap-csv-journal-entries` | `brnz_journal_entries` |
  | Plants batches | `load_plants_batches` | `plants_batches/plants_batches.csv` | `tap-csv-plants-batches` | `brnz_plants_batches` |

- The run, one task after the other (`DataWarehouseAirflow/dags/load_datasets.py`):
  - `no_open_load`: stops the run when the dataset has a load still `landed` or `accepted` (see pitfalls)
  - `make_load_id`, `ingest`: a new uuidv7, and Meltano appends the file to bronze with it as `load_id` on every row
  - `landed`, `audit`: `stg_<dataset>` holds that load alone, and its data tests judge it. One Airflow task per dbt
    node, so the UI shows which test refused it
  - `accepted`, `publish`: silver merges the load, then gold is built on it, in the `publish` pool (one at a time
    across every dataset)
  - `published`: the load is in silver and gold
- The state of every load is one row in `dw_control.ctl_loads`, written only by the DAG:
  `select * from dw_control.ctl_loads order by load_id desc;`
- Passed: `published`, silver holds the load. A row with the same key as one already in silver replaces it, with a
  warning
- Refused: a data test failed or dbt errored in `audit`. The load stays in bronze as a record of what arrived, and
  silver keeps what it had. Fix the file where it came from and trigger the DAG again: every run is a new load
- Failed: `publish` failed. Silver may hold the load already: look before sending the file again
- `tap-csv` alone is the base the extractors inherit from: it has no file, so running it fails
- Each Meltano run is a row in `runs` of the `meltano` database

**See what failed or warned in a load**

- The Airflow UI: the run → the red task → its log
- Row by row, from Elementary's tables, with the load's `load_id` (from `ctl_loads`, or the `make_load_id` task) and
  `<table>` from the table above:

  ```sql
  select r.table_name, r.column_name, r.test_short_name, r.status, rr.result_row
  from dw_elementary.elementary_test_results as r
  inner join dw_elementary.test_result_rows as rr on rr.elementary_test_results_id = r.id
  inner join dw_bronze.<table> as b on b.row_id = (rr.result_row::json ->> 'row_id')::uuid
  where r.status in ('fail', 'warn') and b.load_id = '<load_id>';
  ```

- A test that errored has no rows: it is in `dw_elementary.elementary_test_results` with status `error`, and in the
  task log

### Dev tools (optional)

All in the dev container, from `/usr/app`:

- `pytest` (no tests yet), `ruff check`, `ruff format`
- `sqlfluff format DataWarehouseDbt/models`, `sqlfluff lint DataWarehouseDbt/models` (the database must be up)
- `meltano config print tap-csv` shows a plugin's config as the run sees it, env vars filled in

### Dev as a copy of prod

- Both stacks up: `powershell -ExecutionPolicy Bypass -File Database\dumps\refresh_dev_from_prod.ps1`

### A new release in prod

- Tag and push the release as in `docs/GIT_STANDARDS.md` (**Releases**), set `RELEASE` in `docker/.env.prod` to it,
  run `03_setup_prod.ps1`
- The first release with Meltano, on a prod database that already exists: create Meltano's database once (it is
  created by itself only on a new volume), then check as in section 5

  ```powershell
  Get-Content Database\00_create_meltano_database.sql | docker exec -i dw-prod-postgres-1 psql -U postgres -d postgres
  ```

---

## Common pitfalls

- **`docker` fails with `Docker Desktop is unable to start`, or a setup script with `docker does not answer`:** open
  Docker Desktop and wait until the engine runs; tick autostart (section 1).
- **`set USER_INPUT_DIR / NICEGUI_PORT / USER_OUTPUT_DIR in the env file`:** `docker/.env` is missing or incomplete.
  The env files live in `docker/`, not in the repo root.
- **Prod command hits dev:** `--env-file docker/.env.prod` was left out.
- **Prod `up` fails with `pull access denied for pipeline` / `webapps`:** the images of `RELEASE` were not built: run `03_setup_prod.ps1`.
- **`03_setup_prod.ps1` fails on `docker/pipeline/Dockerfile` not found:** `RELEASE` is a tag from before the pipeline image. Tag
  a release that has it.
- **`no_open_load` fails with `has an open load`:** an earlier run stopped between a dbt step and its state write (a
  database outage), and left its load `landed` or `accepted`. Look at it in `dw_control.ctl_loads`, end it by hand
  (`update dw_control.ctl_loads set state = 'refused', updated_at = clock_timestamp() where load_id = '<load_id>';`,
  or `'failed'` when its publish had started), then trigger the DAG again.
- **A good file is refused with `could not translate host name "postgres"`, or another connection error:** postgres
  was recreated during the run (see the compose pitfall below). The audit has no retries: trigger the DAG again.
- **No load DAGs in the Airflow UI, an import error about `manifest.json`:** Airflow's manifest is missing:
  `airflow-init` failed, or the release's folder is new. Look at the `airflow-init` container's log, then run
  `02_setup_dev.ps1` (or `03_setup_prod.ps1`) again.
- **A new dbt model or test has no task in the DAG:** Airflow's manifest is from before it. Refresh it (see
  **Daily workflow**); in prod it comes with the next release.
- **`03_setup_prod.ps1` stops with `uncommitted changes`:** commit or stash, then run it again.
- **Port 5432 already in use:** a PostgreSQL installed on Windows (old setup). Stop it: `Get-Service *postgres*`,
  then `Stop-Service <name>` and set it to **Manual** in Services.
- **Reset dev** (deletes dev's database; the fix for the next three pitfalls): close the dev container window, then

  ```powershell
  docker compose -f docker/compose.yaml -f docker/compose.dev.yaml --profile job --profile dev down
  docker volume rm dw-dev_pgdata dw-dev_meltano-plugins dw-dev_dbt-state dw-dev_airflow-logs
  powershell -ExecutionPolicy Bypass -File docker\02_setup_dev.ps1
  ```

  - Without the two `--profile`, `down` leaves the job and dev containers running on the old network
  - Also deletes the `airflow` database (every DAG run), the `meltano` database (Meltano's run history), dev's Meltano
    plugins, and everything in `dbt-state` (dbt packages, Airflow's manifest, the other roles' folders): the setup script makes them again, and builds the seeds, every model and
    Elementary's tables before the first load
  - Not `down -v`: it would also delete `dw-dev_claude-config`, Claude Code's login, settings and memory
- **Password changed in `.env`, login fails:** the password is applied only when the volume is created. Either
  `ALTER USER postgres PASSWORD '...'` in the database, or reset dev.
- **DDL changed, nothing happens:** `00_create_meltano_database.sql` and `01_create_schemas_and_tables.sql` run only on
  an empty volume. Reset dev.
- **A Meltano plugin added or changed in `meltano.yml`, the run does not see it:** `meltano install` in the dev
  container. In dev the plugins live in the `dw-dev_meltano-plugins` volume, not in the repo: their venvs hold linux
  symlinks that Windows and OneDrive cannot read, and that broke the image build when they were in
  `DataWarehouseMeltano/.meltano`.
- **`meltano add extractor tap-csv` fails with `Utility 'extractor' is not known`:** Meltano 4 takes the type as an
  option: `meltano add --plugin-type extractor tap-csv`. Then pin `pip_url` to a version in `meltano.yml`.
- **Never `down -v` on prod:** it deletes the database.
- **CSV empty in the container:** a cloud-only OneDrive file. **Always keep on this device**.
- **Excel query shows "no visible columns":** wrong credentials in Power Query, not a database problem.
  **Data Source Settings** → edit the credentials.
- **`dbt run`:** use `dbt build`. `dbt run` on a view drops every view on top of it (`CASCADE`).
- **`dbt_utils` not found in dev:** `dbt deps` in the dev container (or run `02_setup_dev.ps1`, section 4). The
  packages live in `/dbt-state/dev/packages` of the `dw-dev_dbt-state` volume, which starts empty.
- **`dbt clean` in dev refuses the folders:** they are in `/dbt-state`, outside the project. Run
  `dbt clean --no-clean-project-files-only`. It clears `interactive` and the packages, never the other roles.
- **`psql -c` from PowerShell loses double quotes** (`"DataWarehouse"`): pipe the SQL through stdin,
  `"SELECT ...;" | docker exec -i dw-dev-postgres-1 psql -U postgres -d DataWarehouse`, or use Git Bash.
- **Git Bash turns a container path into a Windows one** (`--workdir /usr/app` becomes `C:/.../Git/usr/app`): put
  `MSYS_NO_PATHCONV=1` in front of the docker command.
- **Excel / VS Code SQL tabs disconnect after a compose command:** running compose from Windows after a Dev Container
  (or the other way round) recreates postgres (`C:\` vs `c:\` in the path). Data is kept; reconnect. For jobs that
  do not need the database, add `--no-deps`.
- **A script is blocked by the execution policy:** run it with `powershell -ExecutionPolicy Bypass -File <script>`.
- **Libraries:** never `pip install` in the dev container terminal. Add the library to the image's
  `docker/<image>/requirements-<venv>.txt` (or `docker/pipeline/requirements-tools.txt` and `requirements-pytest.txt` for a dev tool) and rebuild.
