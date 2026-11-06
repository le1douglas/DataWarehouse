# Images, volumes and the dev container

What runs where, split into three layers: **core** (needed to run, the same in dev and prod), **dev** (development
only) and **prod**.

## Core: needed to run, in dev and prod

- **Images:** the `runtime` stage of each `docker/<image>/Dockerfile`, its only stage. Each one holds only what its job
  needs to run.
  - `dbt`: dbt-core, dbt-postgres and git, with the dbt project and its packages (`dbt deps` at build).
  - `meltano`: meltano[postgres] and git, with the meltano project and its plugins (`meltano install` at build).
  - `webapps`: nicegui, SQLAlchemy and psycopg, with `src/webapps`.
  - `datastreamer`: the standard library only, with `src/bluelab_datastreamer`.
  - `postgres:18`: the stock image, configured in `docker/compose.yaml`.
- **Versions:** `docker/<image>/requirements.txt`, the only place a runtime library's version is written. The meltano
  plugins are pinned in `DataWarehouseMeltano/meltano.yml`, and the dbt packages in `DataWarehouseDbt/packages.yml`.
- **Volume:** `pgdata`, the database. Each environment has its own: `dw-dev_pgdata` and `dw-prod_pgdata`.

## Dev: development only

- **Image:** `docker/dev/Dockerfile`, the dev container. It has one venv per image under `/opt/venvs/`, each installed
  from that image's requirements file, so it has the same versions and no clashes. It adds one venv of tools
  (`docker/dev/requirements.txt`) and pytest in the webapps venv (`docker/dev/requirements-test.txt`). All the venvs
  are on `PATH`, and `python` is the webapps one.
- **Volumes**, declared only in `docker/compose.dev.yaml`, so they exist only as `dw-dev_*`:

  | Volume | Holds | Mounted at | Refilled by |
  |---|---|---|---|
  | `meltano-plugins` | the plugin venvs | `DataWarehouseMeltano/.meltano` | `meltano install` |
  | `dbt-state` | `dbt_packages`, `target`, `logs` | `/dbt-state` | `dbt deps`, any dbt command |
  | `claude-config` | Claude Code's login, settings, skills, memory | `/claude-config` | nothing: carry it |

- **Also dev only:** the repo bind mount at `/usr/app`, `WATCHFILES_FORCE_POLLING`, and the read-only `/dumps` on the
  postgres service (not in the dev container: the dumps are restored by postgres).
- **The services in dev** build the same runtime stage as prod, with the repo mounted on top. The dev tools are only
  in the dev container.

## Prod

- The runtime images of the git tag in `RELEASE`, with nothing mounted. `docker/compose.prod.yaml` and `docker/.env.prod`.
- The only volume is `dw-prod_pgdata`. Plugins and packages come from the image. `target` and `logs` are thrown away
  with the container.

## The dev container

- `.devcontainer/dev/devcontainer.json`, the `dev` service. It's in the `dev` profile, so `up` doesn't start it.
- It has the same mounts and env vars as the services, so a load, a build or a reading behaves the same as in a
  service. `dbt` and `meltano` work from any folder (`DBT_PROJECT_DIR`, `MELTANO_PROJECT_ROOT`).
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

- The repo, and the folders shared with the containers: `EXPORTS_DIR`, `DAILY_RAW_CSV_DIR` and `Database/dumps`.
- Docker Desktop, VS Code with Dev Containers, Excel, and the PostgreSQL extension.
- The OnePen bridge (`onepen_bridge.py` with bleak, started by `OnePen.cmd`), because the Bluetooth adapter is on
  Windows.
- The setup scripts `docker/0*_setup_*.ps1`.
