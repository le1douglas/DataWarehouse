# Docker implementation

Installation guide for setting the project up for the first time with Docker, on a Windows 11 PC with nothing
installed. The design is in [DOCKER_PLAN.md](DOCKER_PLAN.md).

## Status

| Phase | Step | Status |
|---|---|---|
| 1 | 1. Install Docker Desktop | Done (2026-10-17) |
| 1 | 2. Postgres in a container | Done (2026-10-17) |
| 1 | 3. The database roles | Postponed (everything connects as `postgres` until then) |
| 1 | 4. The `dbt` image | Done (2026-10-18) |
| 1 | 5. The `loader` image | Done (2026-10-18) |
| 1 | 6. Grafana | Not started |

**Resume at:** phase 1, step 6, Grafana.

## 1. Install Docker Desktop

### 1.1 Check virtualization

Task Manager (`Ctrl + Shift + Esc`) → **Performance** → **CPU** → **Virtualization** must say **Enabled**. If it says
Disabled, enable Intel VT-x / AMD-V in the BIOS/UEFI first.

### 1.2 Update WSL

In PowerShell:

```powershell
wsl --update
wsl --version
```

Expected: a list of versions, starting with `WSL version: 3.0.1.0` or later.

### 1.3 Install Docker Desktop

1. Download from https://www.docker.com/products/docker-desktop/, **Download for Windows – AMD64** (ARM64 only for
   Snapdragon/ARM PCs).
2. Run `Docker Desktop Installer.exe`, choose **install for all users**. The per-user install fails.
3. Configuration screen: **Use WSL 2 instead of Hyper-V** checked.
4. **Close**, then restart the PC.

### 1.4 First start

Open Docker Desktop: accept the agreement, skip the sign-in, skip the survey. Expected: the bottom-left corner shows the
engine running.

**Settings** → **General** → check **Start Docker Desktop when you sign in to your computer** → **Apply**. Without it,
the engine is stopped after every restart of the PC, and every `docker` command fails with
`Docker Desktop is unable to start` until Docker Desktop is opened.

### 1.5 Check from PowerShell

In a new PowerShell window:

```powershell
docker version
```

Expected: a `Client:` block with `OS/Arch: windows/amd64` and a `Server: Docker Desktop ...` block with
`OS/Arch: linux/amd64`.

### 1.6 VS Code extension (recommended)

Extensions view (`Ctrl + Shift + X`) → **Container Tools**, publisher **Microsoft** (`ms-azuretools.vscode-containers`)
→ **Install**. Expected: a **Containers** icon in the sidebar, listing the containers and images of Docker Desktop.

## 2. Postgres in a container

### 2.1 Create `.env`

In the repo root, a file named `.env` (ignored by git):

```
POSTGRES_DB=DataWarehouse
POSTGRES_USER=postgres
POSTGRES_PASSWORD=choose-a-password
POSTGRES_PORT=5432
RELEASE=dev
```

No spaces around `=`, no quotes, no `$` or `#` in the password. Compose reads `.env` from the repo root by itself, so no
command passes `--env-file`, and the Dev Containers read it too. It is the dev env file; prod will get its own.

Check:

```powershell
git status --short --ignored .env
```

Expected: `!! .env`.

### 2.2 Check `compose.yaml`

`compose.yaml` is in the repo root. Check that it reads `.env`:

```powershell
docker compose -p dw-dev config
```

Expected: the file with the values filled in (`POSTGRES_DB: DataWarehouse`, `published: "5432"`), and the volume named
`dw-dev_pgdata`. The output shows the password in plain text.

### 2.3 Start the stack

From the repo root:

```powershell
docker compose -p dw-dev up -d
```

In Docker Desktop, **Containers** → group **dw-dev** → `dw-dev-postgres-1` → **Logs**. Expected, in this order:

```
/usr/local/bin/docker-entrypoint.sh: running /docker-entrypoint-initdb.d/01_create_schemas_and_tables.sql
BEGIN
DO
CREATE SCHEMA
CREATE SCHEMA
CREATE TABLE        (four times)
COMMIT
...
PostgreSQL init process complete; ready for start up.
...
LOG:  database system is ready to accept connections
```

The script runs only when the volume is empty. If it fails, delete the stack with its volume
(`docker compose -p dw-dev down -v`), fix the script, and run `up` again.

### 2.4 Check inside the container

Docker Desktop, `dw-dev-postgres-1` → **Exec** (paste with `Ctrl + Shift + V` or right-click; or run the same command
from PowerShell with `docker exec dw-dev-postgres-1 psql ...`):

```sh
psql -U postgres -d DataWarehouse -c "SHOW timezone;" -c "SELECT now();"
psql -U postgres -d DataWarehouse -c "\dt dev_*.*"
```

Expected: `Europe/Amsterdam`, a `now()` with the Amsterdam offset (`+02` in summer, `+01` in winter), and four tables:
`dev_bronze.brnz_journal_entries`, `dev_bronze.meta_bronze`, `dev_corrections.corr_journal_entries`,
`dev_corrections.meta_corrections`.

After changing `compose.yaml` or `.env`, apply it with `up -d` (it recreates the container and keeps the volume); a
restart keeps the old settings.

### 2.5 Connect from VS Code

PostgreSQL sidebar (Microsoft's PostgreSQL extension) → add connection: host `localhost`, port `5432`, database
`DataWarehouse`, user `postgres`, the password from `.env`. Right-click the database → **New Query**:

```sql
SELECT version();
SHOW timezone;
```

Expected: `PostgreSQL 18.6 (Debian ...) on x86_64-pc-linux-gnu ...` (Debian means the container) and `Europe/Amsterdam`.

### 2.6 ODBC data source for Excel

The psqlODBC driver runs on Windows. Without a Windows PostgreSQL install, download the 64-bit installer (`.msi`) from the
download page linked at https://odbc.postgresql.org and install it.

Start → **ODBC Data Sources (64-bit)**:

1. **Drivers** tab: `PostgreSQL Unicode(x64)` is listed.
2. **System DSN** tab → **Add** → `PostgreSQL Unicode(x64)`:
   - **Data source name:** `PostgreSQL_DataWarehouse`
   - **Database:** `DataWarehouse`
   - **Server:** `localhost`
   - **User Name:** `postgres`
   - **SSL Mode:** `disable`
   - **Port:** `5432`
   - **Password:** the one in `.env`
3. **Test**. Expected: **Connection successful**. Then **Save**.

## 4. The `dbt` image

dbt reads its connection from `DataWarehouseDbt/profiles.yml` (in git), which takes every value from environment
variables.

### 4.1 Create `.env.transformer`

In the repo root, a file named `.env.transformer` (ignored by git):

```
# connection for the dbt container, read by DataWarehouseDbt/profiles.yml. not in git
# host is the postgres service name in compose.yaml: containers of one compose project reach each other by service name
DBT_HOST=postgres
# the port inside the docker network, where the postgres container always listens (5432).
# not POSTGRES_PORT from .env, which is the port published to Windows and changes per environment
DBT_PORT=5432
DBT_DBNAME=DataWarehouse
# postgres until the roles exist (step 3, postponed), then the transformer role
DBT_USER=postgres
DBT_ENV_SECRET_PASSWORD=the POSTGRES_PASSWORD from .env
# time zone of the container (its clock and date). dbt itself always logs in UTC, whatever this says
TZ=Europe/Amsterdam
```

Check:

```powershell
git status --short --ignored .env.transformer
```

Expected: `!! .env.transformer`.

### 4.2 Check the `dbt` service

```powershell
docker compose -p dw-dev --profile job config
```

Expected: a `dbt:` service next to `postgres:`, with `image: dbt:dev`, `profiles: [job]`, `build:` with
`dockerfile: docker/dbt/Dockerfile`, and `environment:` with the five `DBT_*` variables. Without `--profile job` the
`dbt` service is not shown. The output shows the passwords in plain text.

### 4.3 Build the image

With Docker Desktop's engine running, from the repo root:

```powershell
docker compose -p dw-dev build dbt
```

The first build takes one to two minutes. Expected: `transferring context:` a few tens of kB, steps `[1/6]` to `[6/6]`,
and at the end `naming to docker.io/library/dbt:dev` and `Image dbt:dev Built`. Docker Desktop → **Images** shows `dbt`
with tag `dev`.

Check what went into the image:

```powershell
docker run --rm --entrypoint ls dbt:dev -a
```

Expected: `.gitignore`, `.user.yml`, `analyses`, `dbt_packages`, `dbt_project.yml`, `logs`, `macros`, `models`,
`package-lock.yml`, `packages.yml`, `profiles.yml`, `seeds`, `snapshots`, `tests`. No `target`.

### 4.4 Check the connection

```powershell
docker compose -p dw-dev run --rm dbt debug
```

Expected: `profiles.yml file [OK found and valid]`, `dbt_project.yml file [OK found and valid]`, `- git [OK found]`,
`host: postgres`, `port: 5432`, `Connection test: [OK connection ok]`, and at the end `All checks passed!`.

### 4.5 Check the dev mount

In dev, `compose.dev.yaml` mounts `DataWarehouseDbt` from the repo into the container, so every dev command passes
both compose files, in this order:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm dbt debug
```

Expected: `All checks passed!`, as in 4.4, and on Windows the files `DataWarehouseDbt\logs\dbt.log` and
`DataWarehouseDbt\.user.yml`, written by dbt in the container. `git status` does not list them.

### 4.6 First `dbt build`

The mount also hides the `dbt_packages` installed in the image, so in dev the packages live in the repo folder
(`DataWarehouseDbt\dbt_packages`, not in git). Install them once; dbt Power User does it too, every time a window opens
in the dbt container:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm dbt deps
```

Expected: `Installing dbt-labs/dbt_utils` and `Installed from version`.

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm dbt build
```

On an empty bronze, expected: `Found 3 models, 2 data tests, 1 operation, 3 snapshots, 3 sources`, every line `OK` or
`PASS`, and at the end `Completed successfully` and `Done. PASS=9 WARN=0 ERROR=0 SKIP=0`. Also expected, and harmless:
`Unable to do partial parsing because profile has changed` (once, when `target` was written by another dbt) and
`[WARNING]: Detected columns with numeric type and unspecified precision/scale ... ['ml', 'ec', 'ph', 'temp']`.

Then, in VS Code on the `localhost:5432` connection:

```sql
SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'dev_%' ORDER BY 1;
```

Expected: `dev_audit`, `dev_bronze`, `dev_candidate`, `dev_corrections`, `dev_silver`, `dev_snapshots`, `dev_staging`.

## 5. The `loader` image

### 5.1 Create `.env.loader`

In the repo root, a file named `.env.loader` (ignored by git):

```
# connection and inputs for the loader container, read by src/datawarehouse/config.py. not in git
# host is the postgres service name in compose.yaml: containers of one compose project reach each other by service name
POSTGRESQL_SERVER=postgres
# the port inside the docker network, where the postgres container always listens (5432).
# not POSTGRES_PORT from .env, which is the port published to Windows and changes per environment
POSTGRESQL_PORT=5432
POSTGRESQL_DB=DataWarehouse
# postgres until the roles exist (step 3, postponed), then the loader role
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=the POSTGRES_PASSWORD from .env
# each input file, relative to its mounted folder: /inbox/exports (EXPORTS_DIR) and /inbox/corrections (CORRECTIONS_DIR)
JOURNAL_ENTRIES_CSV=drip_drain_csv/journal-entries.csv
CORRECTIONS_WORKBOOK=journal_entries_corrections.xlsx
# time zone of the container: CSVReader stamps meta_extract_date_time with the container's local time
TZ=Europe/Amsterdam
```

Check:

```powershell
git status --short --ignored .env.loader
```

Expected: `!! .env.loader`.

### 5.2 Input folders in `.env`

Add to `.env`, with the Windows folders of the CSV exports and of the corrections workbook (both must exist, even
when the folder has no workbook yet):

```
# windows folders mounted read only into the loader container. each can move: change the line, no rebuild needed
# the root of the csv exports, mounted at /inbox/exports
EXPORTS_DIR=./SampleData
# the folder of the corrections workbook, mounted at /inbox/corrections
CORRECTIONS_DIR=C:/Users/<you>/Desktop
```

Relative paths start at the repo root. Use forward slashes.

### 5.3 Check the `loader` service

```powershell
docker compose -f compose.yaml -f compose.dev.yaml --profile job config
```

Expected, under `loader:`: `image: loader:dev`, `profiles: [job]`, the eight variables of `.env.loader` under
`environment:`, and three `type: bind` volumes: `EXPORTS_DIR` on `/inbox/exports` and `CORRECTIONS_DIR` on
`/inbox/corrections`, both `read_only: true`, and the repo's `src` on `/usr/app/src`. If `EXPORTS_DIR` or
`CORRECTIONS_DIR` is missing from `.env`, compose stops with `set EXPORTS_DIR in the env file`.

### 5.4 Build the image and load bronze

```powershell
docker compose -f compose.yaml -f compose.dev.yaml build loader
```

Expected: `transferring context:` a few tens of kB, steps `[1/4]` to `[4/4]`, `Image loader:dev Built`.

The bronze load appends: on a bronze that already holds the same CSV it duplicates every row. Load once:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm loader bronze
```

Expected: `Loading CSV file: /inbox/exports/drip_drain_csv/journal-entries.csv`, `Connection successful`,
`Loaded <n> rows into dev_bronze.brnz_journal_entries` and `Loaded <2n> rows into dev_bronze.meta_bronze`, and in
the printed first row a `meta_extract_date_time` in local time (Amsterdam), not UTC.

### 5.5 `dbt build` on the loaded data

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm dbt build
```

Before any corrections, the data tests flag rows and silver is skipped: this is the first half of the loop, not a
problem with the setup. With the sample CSV, expected: `FAIL 1 aud_journal_entries__castable`,
`FAIL 8 aud_journal_entries__position_index_max_4`, `SKIP` for `dev_silver.slvr_journal_entries` and
`dev_snapshots.snap_slvr_journal_entries`, the `on-run-end` hook `OK`, and
`Done. PASS=5 WARN=0 ERROR=2 SKIP=2`. The command exits with an error, so Docker prints its "What's next" lines.
The flagged rows are in `dev_audit.aud_journal_entries` (9 rows), candidate has every row of bronze.

### 5.6 Load corrections and build silver

With the reviewed workbook saved as `CORRECTIONS_WORKBOOK` in `CORRECTIONS_DIR`, and closed in Excel (an open
workbook cannot be read):

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm loader corrections
docker compose -f compose.yaml -f compose.dev.yaml run --rm dbt build
```

Expected from the load: `Loading Excel file: /inbox/corrections/<workbook>`, `Connection successful`,
`Loaded <n> rows into dev_corrections.corr_journal_entries`, `Loaded <2n> rows into dev_corrections.meta_corrections`.
When the corrections fix every flagged row, expected from the build: both tests `PASS`,
`OK created sql table model dev_silver.slvr_journal_entries`, `Done. PASS=9 WARN=0 ERROR=0 SKIP=0`, and
`dev_audit.aud_journal_entries` empty.

### 5.7 Check Excel

New blank workbook → **Data** → **Get Data** → **From Other Sources** → **From ODBC** → DSN `PostgreSQL_DataWarehouse`
→ **OK** (if asked for credentials: **Default or Custom** → **Connect**). In the **Navigator**, check **Select multiple
items**, select `dev_candidate.cand_journal_entries`, `dev_audit.aud_journal_entries` and
`dev_silver.slvr_journal_entries`, then **Load**.

Expected in **Queries & Connections**: candidate and silver with every row of bronze, silver's `date_time` as a date
and time. The audit table has only its headers (`row_id`, `kind`, `description`) when the last build flagged nothing,
and one row per flagged row and failed test otherwise.
