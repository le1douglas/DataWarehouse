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
  - **Initial branch name:** `master`
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
- The Python, ruff, dbt Power User extensions are **not** installed on Windows: the dev containers install them

### psqlODBC (for Excel)

- Download the 64-bit `.msi` from [odbc.postgresql.org](https://odbc.postgresql.org) (Downloads → MSI) and install it
- No PostgreSQL server on Windows: the database runs in Docker

---

## 2. Get the repo

- `cd` into the parent folder, then:
  - `git clone https://github.com/le1douglas/DataWarehouse.git`
  - `cd DataWarehouse`
- If the repo is inside OneDrive: right-click the repo folder → **Always keep on this device**
  - A cloud-only file is empty for a container (workbook, CSV, env files)

---

## 3. Create what git does not carry

`git clone` brings none of these. Nothing works until the required ones exist.

| What | Where | Required | How |
|---|---|---|---|
| Six env files: `.env`, `.env.loader`, `.env.transformer`, `.env.prod`, `.env.prod.loader`, `.env.prod.transformer` | `docker/` | yes | the script below |
| dbt packages (`dbt_utils`) | `DataWarehouseDbt/dbt_packages/` | yes, in dev | `setup_dev.ps1`, section 4 |
| Dev corrections workbook `journal_entries_corrections.xlsx` | `user_input/corrections_dev/` | yes, in dev | copy of the prod one, section 6 |
| Prod dumps `*.dump` | `Database/dumps/` | no | written by `refresh_dev_from_prod.ps1` |

### Env files

- `powershell -ExecutionPolicy Bypass -File docker\create_env_files.ps1`
  - Asks a password for dev, then for prod
  - No spaces, quotes, `$` or `#` in a password
  - Existing files: answers `N` keep them and create only the missing ones
  - `RELEASE` in `.env.prod` is the newest git tag at that moment
- Check: `git status --short --ignored docker` lists all six with `!!`

---

## 4. Dev stack

- `powershell -ExecutionPolicy Bypass -File docker\setup_dev.ps1`
  - Starts postgres, builds the `dbt` and `loader` images, runs `dbt deps` and `dbt debug`
  - First run takes a few minutes; safe to run again; stops at the first failing step
  - Ends with `dev setup done`

### Check

- Docker Desktop → **Containers** → group `dw-dev` → `dw-dev-postgres-1` running
- `docker exec dw-dev-postgres-1 psql -U postgres -d DataWarehouse -c "SHOW timezone;"` → `Europe/Amsterdam`
- `docker exec dw-dev-postgres-1 psql -U postgres -d DataWarehouse -c "SELECT now();"` → Amsterdam offset (`+01`
  winter, `+02` summer)
- `docker exec dw-dev-postgres-1 psql -U postgres -d DataWarehouse -c "\dt dw_*.*"` → `brnz_journal_entries`,
  `meta_bronze`, `corr_journal_entries`, `meta_corrections`
- `docker image ls` → `dbt` and `loader`, tag `dev`
- `Test-Path DataWarehouseDbt\dbt_packages\dbt_utils` → `True`
- `docker compose -f docker/compose.yaml -f docker/compose.dev.yaml run --rm dbt build` → `Completed successfully`
  on the empty bronze

---

## 5. Prod stack

- Prod runs the images of the git tag in `RELEASE` (`docker/.env.prod`), with no code mounted
- **Always** pass `--env-file docker/.env.prod`: without it compose reads dev's `.env`

- No uncommitted changes (commit or stash first): the build switches the repo to the tag
- `powershell -ExecutionPolicy Bypass -File docker\setup_prod.ps1`
  - Builds the `dbt` and `loader` images of `RELEASE` from the tag's code, then switches the repo back
  - Images of `RELEASE` that exist are not rebuilt
  - Starts postgres, runs `dbt debug`
  - Safe to run again; stops at the first failing step
  - Ends with `prod setup done, on <RELEASE>`

### Check

- Docker Desktop → **Containers** → group `dw-prod` → `dw-prod-postgres-1` running
- `docker exec dw-prod-postgres-1 psql -U postgres -d DataWarehouse -c "SHOW timezone;"` → `Europe/Amsterdam`
- `docker exec dw-prod-postgres-1 psql -U postgres -d DataWarehouse -c "\dt dw_*.*"` → the same four tables as dev
- `docker image ls` → `dbt` and `loader`, tag = `RELEASE`
- `docker compose -f docker/compose.yaml -f docker/compose.prod.yaml --env-file docker/.env.prod run --rm dbt debug`
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
- The names must match exactly: the workbooks' Power Query refers to them

### Workbooks

- Prod: `user_input/corrections_prod/journal_entries_corrections.xlsx`, in git, already on DSN
  `PostgreSQL_DataWarehouse_Prod`
- Dev: not in git, made from the prod one:
  - `mkdir user_input\corrections_dev`
  - `copy user_input\corrections_prod\journal_entries_corrections.xlsx user_input\corrections_dev\`
  - Open the copy → **Data** → **Get Data** → **Launch Power Query Editor**: in every query, change
    `dsn=PostgreSQL_DataWarehouse_Prod` to `dsn=PostgreSQL_DataWarehouse` → **Close & Load** → save
  - Never edit the prod workbook for dev: it is released with each tag
- Check, in each workbook: **Data** → **Refresh All**, no errors
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

### Dev containers

- `code .` from the repo root
- `Ctrl + Shift + P` → **Dev Containers: Reopen in Container** → pick `dbt`
  - First open installs the extensions in the container and runs `dbt deps`
  - Back to Windows: **Dev Containers: Reopen Folder Locally**
- The same for `loader`

Setup is done.

---

## Daily workflow

### The loop

- Each step runs either from PowerShell (repo root) or in the VS Code terminal of a dev container (opens at `/usr/app`)
- Stick to one of the two in a session: switching recreates postgres and drops Excel's connection (see pitfalls)
- Prod: the same PowerShell commands with `-f docker/compose.prod.yaml --env-file docker/.env.prod` instead of
  `-f docker/compose.dev.yaml`, and the prod workbook

**1. Load bronze, once per CSV** (a second run duplicates every row)

- PowerShell:

  ```powershell
  docker compose -f docker/compose.yaml -f docker/compose.dev.yaml run --rm loader bronze
  ```

- `loader` container:

  ```sh
  python -m datawarehouse bronze
  ```

**2. Build**

- PowerShell:

  ```powershell
  docker compose -f docker/compose.yaml -f docker/compose.dev.yaml run --rm dbt build
  ```

- `dbt` container:

  ```sh
  cd DataWarehouseDbt
  dbt build
  ```

- Rows that need a correction: tests `FAIL` and silver is `SKIP`

**3. Review in Excel**

- Workbook → **Data** → **Refresh All** → fill the corrections → save → **close Excel**

**4. Load the corrections**

- PowerShell:

  ```powershell
  docker compose -f docker/compose.yaml -f docker/compose.dev.yaml run --rm loader corrections
  ```

- `loader` container:

  ```sh
  python -m datawarehouse corrections
  ```

**5. Build again**

- Same command as step 2: tests `PASS`, `OK created sql table model dw_silver.slvr_journal_entries`

### Dev tools (optional)

- `loader` container: `pytest` (some tests are known to fail, see `docs/REMINDERS.md`), `ruff check`, `ruff format`
- `dbt` container, from `/usr/app`: `sqlfmt DataWarehouseDbt/models DataWarehouseDbt/tests`

### Dev as a copy of prod

- Both stacks up: `powershell -ExecutionPolicy Bypass -File Database\dumps\refresh_dev_from_prod.ps1`

### A new release in prod

- `git tag` the release, set `RELEASE` in `docker/.env.prod` to it, run `setup_prod.ps1`

---

## Common pitfalls

- **`docker` fails with `Docker Desktop is unable to start`:** open Docker Desktop; tick autostart (section 1).
- **`set EXPORTS_DIR / CORRECTIONS_DIR / DAILY_RAW_CSV_DIR in the env file`:** `docker/.env` is missing or incomplete.
  The env files live in `docker/`, not in the repo root.
- **Prod command hits dev:** `--env-file docker/.env.prod` was left out.
- **Prod `up` fails with `pull access denied for dbt` / `loader`:** the images of `RELEASE` were not built: run `setup_prod.ps1`.
- **`setup_prod.ps1` stops with `uncommitted changes`:** commit or stash, then run it again.
- **Port 5432 already in use:** a PostgreSQL installed on Windows (old setup). Stop it: `Get-Service *postgres*`,
  then `Stop-Service <name>` and set it to **Manual** in Services.
- **Password changed in `.env`, login fails:** the password is applied only when the volume is created. Either
  `ALTER USER postgres PASSWORD '...'` in the database, or on dev reset: `down -v`, then `up -d` (loses dev's data).
- **DDL changed, nothing happens:** `01_create_schemas_and_tables.sql` runs only on an empty volume. On dev:
  `docker compose -f docker/compose.yaml -f docker/compose.dev.yaml down -v`, then `up -d`.
- **Never `down -v` on prod:** it deletes the database.
- **`loader bronze` twice:** duplicates every row. On dev: reset (`down -v`, `up -d`) and load once.
- **`loader corrections` fails with `PermissionError`:** the workbook is open in Excel. Close it.
- **Workbook or CSV empty in the container:** a cloud-only OneDrive file. **Always keep on this device**.
- **Excel query shows "no visible columns":** wrong credentials in Power Query, not a database problem.
  **Data Source Settings** → edit the credentials.
- **`dbt run`:** use `dbt build`. `dbt run` on a view drops every view on top of it (`CASCADE`).
- **`dbt build` in the `dbt` container fails with `No dbt_project.yml found`:** `cd DataWarehouseDbt` first.
- **`dbt_utils` not found in dev:** run `setup_dev.ps1` (section 4), or open the `dbt` dev container once.
- **`psql -c` from PowerShell loses double quotes** (`"DataWarehouse"`, `"position"`): pipe the SQL through stdin,
  `"SELECT ...;" | docker exec -i dw-dev-postgres-1 psql -U postgres -d DataWarehouse`, or use Git Bash.
- **Excel / VS Code SQL tabs disconnect after a compose command:** running compose from Windows after a Dev Container
  (or the other way round) recreates postgres (`C:\` vs `c:\` in the path). Data is kept; reconnect. For jobs that
  do not need the database, add `--no-deps`.
- **A script is blocked by the execution policy:** run it with `powershell -ExecutionPolicy Bypass -File <script>`.
- **Libraries:** never `pip install` in a dev container terminal; add the library to the Dockerfile and rebuild.
