# Docker plan

How the project moves from programs installed on Windows to Docker containers, with a dev environment that can be reset
in a minute and, later, a prod environment and OpenMetadata. This is the target architecture, not the current state:
nothing here is implemented yet.

## Scope

| Phase | What | Status |
|---|---|---|
| 1 | The dev compose: postgres, loader, dbt, grafana | **Next** |
| 2 | Prod: a second copy of the same compose, releases, migrations, backups | Later |
| 3 | OpenMetadata, as its own stack shared by dev and prod | Later |

Only phase 1 is to be implemented now. Phases 2 and 3 are described so that phase 1 does not block them.

## Docker vocabulary

- **Image:** a packaged, read-only template of a program and everything it needs (`postgres:18`, `grafana/grafana`).
- **Container:** a running instance of an image. It can be deleted and recreated in seconds.
- **Volume:** where a container keeps data that must outlive it, such as the database files. Deleting a container
  keeps its volume; deleting the volume deletes the data.
- **Network:** containers of one compose project reach each other by service name (`postgres:5432`). Windows reaches
  them through **published ports** (`localhost:5432`).
- **Compose file:** a YAML file listing the containers, volumes and networks of a stack. `docker compose up` starts it,
  `docker compose down` stops it.
- **Tag:** the label after the colon of an image name (`loader:1.4`), used to tell versions apart.

Docker Desktop on Windows 11 Home runs on WSL2 (Home has no Hyper-V). Docker installs and manages its own Linux, there
is no Ubuntu to maintain.

## What stays on Windows

Docker runs Linux programs, so the desktop tools stay where they are and connect to the containers through published
ports:

- **Excel**, its Power Query and the ODBC DSN (one DSN per environment, each on its own port).
- **Power BI Desktop**, with the PostgreSQL connector on `localhost:<port>`. Scheduled refresh in the Power BI Service
  needs Microsoft's on-premises data gateway installed on Windows.
- **VS Code**, Git, and the browser for Grafana and OpenMetadata.

## Overview

```
Windows: Excel, Power BI, VS Code, browser
   │  localhost:5432           │  localhost:5433           │ localhost:8585
   ▼                           ▼                           ▼
┌─ dw-dev ──────────┐   ┌─ dw-prod ─────────┐   ┌─ tools ─────────────────┐
│ postgres          │   │ postgres          │   │ openmetadata-server     │
│ loader  (job)     │   │ loader  (job)     │   │ opensearch              │
│ dbt     (job)     │   │ dbt     (job)     │   │ openmetadata-db         │
│ grafana :3000     │   │ grafana :3001     │   │ ingestion (Airflow)     │
│ volume: pgdata    │   │ volume: pgdata    │   │                         │
└───────────────────┘   └───────────────────┘   └─────────────────────────┘
   phase 1                 phase 2                 phase 3
        same compose file,                         its own compose file,
        different env file                         reads both warehouses
```

## The warehouse stack

One compose file, `compose.yaml`, defines the warehouse. Dev and prod are two runs of it under different project names
and env files, so prod runs exactly what was tested in dev:

```
docker compose -p dw-dev  --env-file .env.dev  up -d
docker compose -p dw-prod --env-file .env.prod up -d
```

### Containers

| Service | Image | Runs | Role |
|---|---|---|---|
| `postgres` | official `postgres:18` | always on | The warehouse, data in a named volume |
| `loader` | own image, `docker/loader/Dockerfile` | a job: starts, does one load, exits | `python -m datawarehouse bronze` / `corrections` |
| `dbt` | own image, `docker/dbt/Dockerfile` | a job | `dbt build` and the other dbt commands |
| `grafana` | official `grafana/grafana` | always on | Dashboards on this environment's postgres |

A job runs with `docker compose run`, for example `docker compose -p dw-dev run dbt build`, and stops when it is done.
The two images replace the `.venv`.

### Why the loader and dbt are two images

The loader and dbt never talk to each other: the loader writes `bronze` and `corrections`, dbt reads them. Their only
contract is the shape of those tables, which the hand-written DDL owns. So they are split:

- **Separate dependencies.** The loader image has Python, pandas, pydantic, openpyxl and the package; the dbt image has
  dbt-core, dbt-postgres and `dbt deps`. Updating one cannot break the other.
- **Logical separation.** Two services, connected only through the database, as in the ownership table in `CLAUDE.md`.
- **The loader can change language.** Only `docker/loader/Dockerfile` and the loader code change; the compose file,
  dbt and the database stay as they are.
- **One database role each.** Each service gets an env file with only its own credentials.

### Same version, always

Both images are built from the same commit and carry the same tag. The compose file does not write a version per
service: both read one variable, so they cannot drift apart.

```yaml
services:
  loader:
    build: { context: ., dockerfile: docker/loader/Dockerfile }
    image: loader:${RELEASE}
    env_file: .env.loader
  dbt:
    build: { context: ., dockerfile: docker/dbt/Dockerfile }
    image: dbt:${RELEASE}
    env_file: .env.transformer
```

`RELEASE` is set once in the environment's env file (`RELEASE=dev`, `RELEASE=1.4`). Changing that one line moves both
images, forwards or back.

### Dev and prod differences

| | dev | prod |
|---|---|---|
| Code in the loader and dbt containers | Mounted from the repo folder, edits apply without a rebuild (`compose.dev.yaml`) | Built into the images of a git tag |
| `RELEASE` | `dev` | The git tag, `1.4` |
| Reset | `down -v`, then `up`: empty database with the DDL applied | Never. Backed up instead |
| Postgres port | 5432 | 5433 |
| Grafana port | 3000 | 3001 |

## Database

### Schema and DDL

The official postgres image creates the database from `POSTGRES_DB` and, the first time it starts on an empty volume,
runs every `.sql` file in `/docker-entrypoint-initdb.d`. `Database/03_create_schemas_and_tables.sql` is mounted there.
The `01_` and `02_` scripts, which create the database, are no longer needed.

The init scripts run **only on an empty volume**. On an existing volume a changed `03_` script does nothing; see
[Migrations](#migrations).

### Roles

One role per responsibility, created by an init script next to the DDL:

| Role | Used by | Rights |
|---|---|---|
| owner | the DDL | owns the schemas and tables of bronze and corrections |
| loader | the `loader` service | writes `bronze` and `corrections` |
| transformer | the `dbt` service | reads `bronze` and `corrections`, owns the layers dbt creates |
| reader | Excel, Grafana, Power BI, OpenMetadata | read only |

This replaces the `postgres` superuser used everywhere today, and closes the TODOs in `INSTALLATION_GUIDE.md` about a
read-only user for the ODBC DSN.

### Schema names

With one database per environment, the environment comes from the connection, and schemas no longer need the `dev_`
prefix (`bronze`, `silver` instead of `dev_bronze`, `dev_silver`). This settles the "source names contain `dev_`"
reminder in `CLAUDE.md`. It is the largest code change of the move, so it is done in phase 2, when prod comes; phase 1
keeps the current names.

### Volumes are the data

In dev, losing the volume is the point of a reset. In prod it would lose bronze, the corrections and all snapshot
history, which cannot be rebuilt: never `down -v` on prod.

## Files shared between Windows and containers

| What | Written by | Read by | How |
|---|---|---|---|
| Repo code | You, in VS Code | dev's `loader` and `dbt` | Folder mounted into the container (dev only) |
| `.env.dev`, `.env.prod`, `.env.loader`, `.env.transformer` | You | compose | On Windows, not in git, like `.env` today |
| `profiles.yml` | You | dbt | Moves into the repo and reads host, user and password with `env_var()`, instead of living in `%USERPROFILE%\.dbt` |
| Corrections workbook, CSV exports | Excel, the Bluelab app | `loader` | One folder per environment (`inbox\dev`, `inbox\prod`), mounted **read only**, so the workbook is never written |
| dbt artifacts (`target/`) | `dbt` | OpenMetadata ingestion (phase 3) | A shared folder |
| Grafana data sources and dashboards | You, in the Grafana UI, then exported | `grafana` | JSON/YAML in the repo (provisioning), so a reset keeps them and prod gets the ones tested in dev |

The paths that are hardcoded in `src/datawarehouse/config.py` today (`CORRECTIONS_WORKBOOK`, `JOURNAL_ENTRIES_CSV`) and
the connection settings become environment variables, because inside a container the host is `postgres` and the files
are at the mounted path.

## Repo layout

```
DataWarehouse/
  compose.yaml             # warehouse stack: postgres, loader, dbt, grafana
  compose.dev.yaml         # dev only: mount the code, dev ports
  docker/loader/Dockerfile
  docker/dbt/Dockerfile
  docker/grafana/          # provisioning: data sources, dashboards
  tools/openmetadata/      # phase 3: their compose file, lightly edited
  Database/                # DDL, roles, migrations/ (phase 2)
  src/  DataWarehouseDbt/  # as now
  .env.*                   # not in git
```

## Phase 1: the dev compose

### Reset

```
docker compose -p dw-dev down -v
docker compose -p dw-dev up -d                         # empty database, DDL and roles applied
docker compose -p dw-dev run loader python -m datawarehouse bronze
docker compose -p dw-dev run dbt build
```

This replaces `.scripts\rebuild.ps1`. A full loop is the same as today, with each step in its container: load bronze,
`dbt build`, review in Excel, load corrections, `dbt build`.

### Steps

One step at a time, each one working before the next:

1. Install Docker Desktop.
2. Postgres in a container, with the DDL from the init folder, published on 5432. The Windows PostgreSQL service is
   stopped (or moved to another port) so the two do not compete for 5432. Excel, VS Code and `psql` keep working
   through `localhost:5432`.
3. The database roles.
4. The `dbt` image, with `profiles.yml` in the repo reading `env_var()`.
5. The `loader` image, with paths and connection from environment variables and the inbox folder mounted read only.
6. Grafana, with its data source and dashboards provisioned from the repo.

### Open points for phase 1

- Where the test suite in `.scratch/pipeline-test-suite/spec.md` runs: a throwaway postgres container is the natural
  fit, and can be added once the dev compose works.
- How the loop is started: by hand with `docker compose run` at first, Windows Task Scheduler or an orchestrator
  (Dagster) later.

## Phase 2: prod

- Started with `-p dw-prod --env-file .env.prod`, on port 5433 and 3001.
- **Release:** commit, `git tag v1.4`, `RELEASE=1.4 docker compose build`, set `RELEASE=1.4` in `.env.prod`. Old images
  stay, so a rollback is setting `RELEASE` back.
- **Downtime is accepted.** An upgrade takes prod down for a few minutes: `down` (never `-v`), change, `up`. The
  containers are recreated, the volume and its data are kept.
- **Backups:** `pg_dump` to a folder outside Docker, scheduled and at the start of every upgrade. Without it, prod in a
  volume is more fragile than the Windows service today.

### Migrations

The tables of bronze and corrections hold data, so in prod a table change is an `ALTER TABLE`, not a drop and recreate
(the `DROP TABLE ... CASCADE` procedure in `CLAUDE.md` only works on an empty table). dbt rebuilds its own layers on
every build and handles the snapshots by its own rules, so migrations only concern the hand-written DDL.

- Numbered scripts in `Database/migrations/` (`001_add_column_x.sql`, ...), part of the release that needs them.
- `03_` is kept up to date as well, so a fresh dev database equals prod after all migrations.
- Upgrade: `pg_dump`, `down`, run the new migrations with `psql -f`, change `RELEASE`, `up`, `dbt build`.
- Later, the migrations can become a small third job image with the same `${RELEASE}`.

### Postgres major version

Going from `postgres:18` to `postgres:19` is not a tag change: the files in the volume belong to the major version.
Dump, start an empty 19, restore.

### One machine

Prod on the same PC is off when the PC is off, and shares its 16 GB with dev. Dev, prod and OpenMetadata together take
about 8 to 10 GB; stop what is not in use. Moving prod to a server later is copying the compose file and `.env.prod`
and restoring a backup.

## Phase 3: OpenMetadata

- Its own stack in `tools/openmetadata/`, from the official compose file almost unchanged: server, OpenSearch, its own
  database, Airflow for ingestion. One copy for both environments, so one catalogue shows dev and prod.
- Reads the warehouses as an outside client, through `host.docker.internal:5432` and `:5433`, with the reader role.
- Reads the dbt artifacts (`manifest.json`, `catalog.json`, `run_results.json`) from the shared folder; `catalog.json`
  needs `dbt docs generate`.
- Runs on 8585. With OpenSearch and Airflow it takes 6 to 8 GB of RAM while running.

## Later additions

- **Scheduler** for "load, then `dbt build`": Windows Task Scheduler first, an orchestrator later.
- **CI:** GitHub Actions running the test suite on a throwaway postgres on every push, before a tag goes to prod.
