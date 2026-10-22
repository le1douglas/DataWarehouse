# Docker plan

How the project moves from programs installed on Windows to Docker containers, with a dev environment that can be reset
in a minute and, later, a prod environment and OpenMetadata. This is the target architecture, not the current state:
nothing here is implemented yet.

## How this plan is implemented

The user implements it by hand, with Docker Desktop, as a learning exercise. An agent guiding them follows these rules,
in every session:

- **One atomic step per response.** If a step is long, it is split into smaller sub-steps, one per response. Each
  response opens with a short progress marker (where we are in the phase and its steps), explains that one step, says
  what to report back, and stops. Later steps are never printed ahead of time.
- **Self-contained responses.** Every response carries everything needed for its step (commands, file contents, why),
  so the user never has to scroll back to an older message.
- **Move on only when told.** The next step starts only when the user says so. Questions about the current step are
  answered within that step.
- **Docker Desktop's UI first.** Every action that can be done in the Docker Desktop app is explained there; the
  command line is used only when the UI cannot do it (for example `docker compose` with its flags), and the response
  says so. The equivalent command can be mentioned for reference.
- **The user does the work.** The agent explains and writes files when asked, but does not run Docker or anything that
  writes to the database on the user's behalf.
- **Keep `docs/DOCKER_IMPLEMENTATION.md` up to date.** It is the installation guide for a new user setting the project
  up for the first time, on a PC with nothing installed. After each step is done, write there only what that user
  needs: the exact actions, commands and files, what they should see, and known problems with their fix. It does not
  explain why; the explanations stay in the conversation.
- **Local time, not UTC.** Wherever a container, image or tool shows or stamps a datetime in UTC by default (logs,
  timestamps, schedules), set it to `Europe/Amsterdam`: `TZ=Europe/Amsterdam` in the service's env file, or the
  program's own time zone setting (such as postgres's `-c timezone=`). Check it after the change, for example with
  `date` in the container. Some programs ignore it: dbt stamps its log lines in UTC whatever `TZ` says. It does not record decisions and their alternatives (they belong in this plan), anything specific to the
  user's own PC (such as stopping a PostgreSQL already installed on Windows), or detours and learning exercises. A new
  session reads it first to know where to resume.

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
docker compose -f compose.yaml -f compose.dev.yaml up -d   # dev: reads .env, the name dw-dev is in compose.dev.yaml
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

The stack is defined only in the compose file, never with Docker Desktop's Run dialog: settings typed in the dialog live
only in that one container, are lost on a reset and are not in git. Docker Desktop cannot create a compose stack, so
`docker compose up` is run from the command line; once running, the stack is managed in Docker Desktop (Containers tab,
grouped under the project name).

Postgres uses the tag `postgres:18` (the latest 18.x), never `latest`, which would move to the next major version on
its own (see [Postgres major version](#postgres-major-version)).

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
  dbt:
    build: { context: ., dockerfile: docker/dbt/Dockerfile }
    image: dbt:${RELEASE}
```

The env files of the loader and dbt are not in `compose.yaml`: each overlay (`compose.dev.yaml`, `compose.prod.yaml`)
sets its own, because compose appends an overlay's `env_file` to the base one instead of replacing it.

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
runs every `.sql` file in `/docker-entrypoint-initdb.d`, in alphabetical order. `Database/01_create_schemas_and_tables.sql`
is mounted there. The scripts that dropped and created the database were deleted; the scripts keep a number prefix for
the order (the roles come after the DDL).

The server's time zone is `Europe/Amsterdam`, set in `compose.yaml` with `-c timezone=... -c log_timezone=...` on the
`postgres` command, so it applies to any volume, new or existing. The image's default is `Etc/UTC`, which would stamp
the snapshots' `meta_valid_from` / `meta_valid_to` (`now()::timestamp`) in UTC.

The init scripts run **only on an empty volume**. On an existing volume a changed `01_` script does nothing; see
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

The roles are postponed in phase 1: dbt, the loader, Grafana and Excel connect as `postgres` until they exist, with
user and password read from their env files, so adding the roles changes only those files. On dev a reset then
recreates dbt's objects under `transformer`. The roles must exist before prod starts (phase 2), and `reader` before
OpenMetadata (phase 3).

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
| `.env` (dev), `.env.prod`, `.env.loader`, `.env.transformer` | You | compose | On Windows, not in git |
| `profiles.yml` | You | dbt | Moves into the repo and reads host, user and password with `env_var()`, instead of living in `%USERPROFILE%\.dbt` |
| Corrections workbook, CSV exports | Excel, the Bluelab app | `loader` | Two folders, each mounted **read only** (so the workbook is never written): the exports at `/inbox/exports`, the corrections at `/inbox/corrections`. See [Input folders](#input-folders) |
| dbt artifacts (`target/`) | `dbt` | OpenMetadata ingestion (phase 3) | A shared folder |
| Grafana data sources and dashboards | You, in the Grafana UI, then exported | `grafana` | JSON/YAML in the repo (provisioning), so a reset keeps them and prod gets the ones tested in dev |

### Input folders

Where the exports and the workbook live day to day is not decided, and they are in different folders. So the
location is a setting, never part of the code or the image:

| Setting | In | Meaning |
|---|---|---|
| `EXPORTS_DIR` | the environment's env file (`.env` in dev) | Windows folder mounted at `/inbox/exports`: the root of every dataset's CSV exports |
| `CORRECTIONS_DIR` | the environment's env file | Windows folder mounted at `/inbox/corrections`: where the corrections workbook is |
| `JOURNAL_ENTRIES_CSV` | `.env.loader` | the CSV of the dataset, relative to `/inbox/exports` (`drip_drain_csv/journal-entries.csv`) |
| `CORRECTIONS_WORKBOOK` | `.env.loader` | the workbook, relative to `/inbox/corrections`. Probably one for every dataset |

Moving a folder is one line in the env file, without a rebuild (mounts are set when a container starts). The two
folders can be unrelated or subfolders of one parent. A new dataset adds its own `<DATASET>_CSV` line, not a mount.
A loader command per dataset (`bronze journal_entries`) is a Python change for when a second dataset comes, not
part of the move. Until the location is decided, `EXPORTS_DIR` points to `SampleData` in the repo. A folder in
OneDrive needs its files set to "Always keep on this device": a cloud-only file has no content for the container.

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
  .env  .env.*             # not in git
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
- `01_` is kept up to date as well, so a fresh dev database equals prod after all migrations.
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
