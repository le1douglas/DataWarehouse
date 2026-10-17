# Docker implementation

Installation guide for setting the project up for the first time with Docker, on a Windows 11 PC with nothing
installed. The design is in [DOCKER_PLAN.md](DOCKER_PLAN.md).

## Status

| Phase | Step | Status |
|---|---|---|
| 1 | 1. Install Docker Desktop | Done (2026-10-17) |
| 1 | 2. Postgres in a container | Done (2026-10-17) |
| 1 | 3. The database roles | Not started |
| 1 | 4. The `dbt` image | Not started |
| 1 | 5. The `loader` image | Not started |
| 1 | 6. Grafana | Not started |

**Resume at:** phase 1, step 3, the database roles. Excel itself is checked once dbt has built candidate (step 4).

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

### 1.5 Check from PowerShell

In a new PowerShell window:

```powershell
docker version
```

Expected: a `Client:` block with `OS/Arch: windows/amd64` and a `Server: Docker Desktop ...` block with
`OS/Arch: linux/amd64`.

## 2. Postgres in a container

### 2.1 Create `.env.dev`

In the repo root, a file named `.env.dev` (ignored by git):

```
POSTGRES_DB=DataWarehouse
POSTGRES_USER=postgres
POSTGRES_PASSWORD=choose-a-password
POSTGRES_PORT=5432
```

No spaces around `=`, no quotes, no `$` or `#` in the password.

Check:

```powershell
git status --short --ignored .env.dev
```

Expected: `!! .env.dev`.

### 2.2 Check `compose.yaml`

`compose.yaml` is in the repo root. Check that it reads `.env.dev`:

```powershell
docker compose -p dw-dev --env-file .env.dev config
```

Expected: the file with the values filled in (`POSTGRES_DB: DataWarehouse`, `published: "5432"`), and the volume named
`dw-dev_pgdata`. The output shows the password in plain text.

### 2.3 Start the stack

From the repo root:

```powershell
docker compose -p dw-dev --env-file .env.dev up -d
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

After changing `compose.yaml` or `.env.dev`, apply it with `up -d` (it recreates the container and keeps the volume); a
restart keeps the old settings.

### 2.5 Connect from VS Code

PostgreSQL sidebar (Microsoft's PostgreSQL extension) → add connection: host `localhost`, port `5432`, database
`DataWarehouse`, user `postgres`, the password from `.env.dev`. Right-click the database → **New Query**:

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
   - **Password:** the one in `.env.dev`
3. **Test**. Expected: **Connection successful**. Then **Save**.
