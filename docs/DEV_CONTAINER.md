# Images, volumes and the dev container

What runs where, split into three layers: **core** (needed to run, the same in dev and prod), **dev** (development
only) and **prod**.

## Core: needed to run, in dev and prod

- **Images:** the `runtime` stage of each `docker/<image>/Dockerfile`, its only stage. Each one holds only what its job
  needs to run.
  - `airflow`: runs every load. Airflow with Cosmos, dbt and Meltano, each in its own venv under `/opt/venvs/` (Airflow's
    constraints would otherwise force their versions on dbt and Meltano), and git. With the dbt project, its packages
    and its manifest (`dbt deps` and `dbt parse` at build), the Meltano project and its plugins (`meltano install` at
    build), and the DAGs. One image, one container per Airflow component (`airflow-api-server`, `airflow-scheduler`,
    `airflow-dag-processor`, and `airflow-init`, which migrates the `airflow` database and exits). The scheduler runs
    every task, so it is the only one that runs dbt and Meltano.
  - `webapps`: nicegui, SQLAlchemy and psycopg, with `src/webapps`.
  - `datastreamer`: the standard library only, with `src/bluelab_datastreamer`.
  - `postgres:18`: the stock image, configured in `docker/compose.yaml`.
- **Versions:** `docker/<image>/requirements.txt`, the only place a runtime library's version is written; the `airflow`
  image has three, `requirements.txt` (Airflow and Cosmos), `requirements-dbt.txt` and `requirements-meltano.txt`.
  The meltano plugins are pinned in `DataWarehouseMeltano/meltano.yml`, and the dbt packages in `DataWarehouseDbt/packages.yml`.
- **Volumes:** each environment has its own, prefixed by its project name (`dw-dev_*`, `dw-prod_*`):
  - `pgdata`, the database.
  - `work-in-progress`, at `/work_in_progress`: what a program has not finished yet, one subfolder per program, such
    as `journal_entries/drip_drain.csv` of the datastreamer. It outlives the container. The dev container mounts
    `dw-dev_work-in-progress` only.
  - `airflow-logs`, at `/opt/airflow/logs`: the task logs, written by the scheduler and read by the UI in the API
    server.

## Dev: development only

- **Image:** `docker/dev/Dockerfile`, the dev container. It has one venv per image under `/opt/venvs/`, each installed
  from that image's requirements file (`airflow`, `dbt` and `meltano` from the three files of the `airflow` image), so
  it has the same versions and no clashes. The `airflow` command reaches dev's `airflow` database. It adds one venv of tools
  (`docker/dev/requirements.txt`) and pytest in the webapps venv (`docker/dev/requirements-test.txt`). All the venvs
  are on `PATH`, and `python` is the webapps one. It also has `psql`, `pg_dump` and `pg_restore` at the server's
  major version, from PostgreSQL's own package source. That version is written in two places, the Dockerfile and
  the `postgres` image tag in `docker/compose.yaml`, which have to change together.
- **Volumes**, declared only in `docker/compose.dev.yaml`, so they exist only as `dw-dev_*`:

  | Volume | Holds | Mounted at | Refilled by |
  |---|---|---|---|
  | `meltano-plugins` | the plugin venvs, shared with the scheduler | `DataWarehouseMeltano/.meltano` | `meltano install` |
  | `dbt-state` | `dbt_packages`, `target` (with the manifest the DAGs are drawn from), `logs`, shared with the scheduler and the DAG processor | `/dbt-state` | `dbt deps`, `dbt parse`, any dbt command |
  | `claude-config` | Claude Code's login, settings, skills, memory | `/claude-config` | nothing: carry it |

- **Also dev only:** the repo bind mount at `/usr/app`, `WATCHFILES_FORCE_POLLING`, and the read-only `/dumps` on the
  postgres service (not in the dev container: the dumps are restored by postgres).
- **The services in dev** build the same runtime stage as prod, with the repo mounted on top. The dev tools are only
  in the dev container. The Airflow scheduler and DAG processor read the repo's DAGs live, and the manifest any dbt
  command of the dev container writes: a new dbt model gets its task after the next `dbt parse`. Cosmos runs each dbt
  task in its own temporary copy of the project, with its own `target` and `logs`, so tasks running at once do not
  share the volume's.

## Prod

- The runtime images of the git tag in `RELEASE`, with nothing mounted. `docker/compose.prod.yaml` and `docker/.env.prod`.
- The only volumes are `dw-prod_pgdata`, `dw-prod_work-in-progress` and `dw-prod_airflow-logs`. Plugins, packages and
  the dbt manifest come from the image. `target` and `logs` are thrown away with the container.

## The dev container

- `.devcontainer/dev/devcontainer.json`, the `dev` service. It's in the `dev` profile, so `up` doesn't start it.
- It has the same mounts and env vars as the services, so a load, a build or a reading behaves the same as in a
  service. `dbt`, `meltano` and `airflow` work from any folder (`DBT_PROJECT_DIR`, `MELTANO_PROJECT_ROOT`,
  `AIRFLOW__CORE__DAGS_FOLDER`).
- **Env var names are listed twice,** in `compose.yaml` for the services and in `compose.dev.yaml` for `dev`. A YAML
  anchor can't reach across files. A new env var on a service needs adding to `dev` too.
- **No Docker inside:** it reaches only the dev database. Restarts and `docker volume` commands are run from Windows.
- **Claude Code** runs inside it, with `CLAUDE_CONFIG_DIR=/claude-config`. Memory is filed under the workspace path
  (`/usr/app`, key `-usr-app`), so `workspaceFolder` must not change.

## Moving Claude Code to another machine

Volumes stay in this machine's Docker. Everything except `claude-config` is rebuilt or refilled from the repo. Run these
from Git Bash at the repo root, with the dev container closed:

```bash
# on the old machine: export the volume to claude-config.tgz in the current folder
MSYS_NO_PATHCONV=1 docker run --rm -v dw-dev_claude-config:/data -v "$PWD":/backup python:3.14-slim \
  tar czf /backup/claude-config.tgz -C /data .

# on the new machine, before opening the dev container: import it into a new volume
MSYS_NO_PATHCONV=1 docker run --rm -v dw-dev_claude-config:/data -v "$PWD":/backup python:3.14-slim \
  tar xzf /backup/claude-config.tgz -C /data
```

`claude-config.tgz` holds the login, so keep it out of git and OneDrive, and delete it once it's imported.

## What stays on Windows

- The repo, and the folders shared with the containers: `USER_INPUT_DIR`, `USER_OUTPUT_DIR` and `Database/dumps`.
- Docker Desktop, Excel, and VS Code with only the Dev Containers extension: the project is opened only in the dev
  container, whose extensions are listed in `devcontainer.json`.
- The OnePen bridge (`onepen_bridge.py` with bleak, started by `OnePen.cmd`), because the Bluetooth adapter is on
  Windows.
- The setup scripts `docker/0*_setup_*.ps1`.
