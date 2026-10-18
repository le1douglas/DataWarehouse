# Windows cleanup

My own checklist for removing from Windows what Docker now replaces, on both PCs. It holds the decisions behind the
cleanup, the way of working that replaces the `.venv`, and the steps to repeat on the other PC. Delete this file once
both PCs are done.

Not to be confused with [DOCKER_IMPLEMENTATION.md](DOCKER_IMPLEMENTATION.md), the installation guide for a new PC,
which holds nothing specific to my own machines.

## Decisions (2026-10-18)

- **As little as possible installed on Windows:** Docker Desktop, VS Code, Git, Excel and the ODBC driver. No Python, no
  `.venv`, no PostgreSQL.
- **Every dev tool lives in the image it belongs to**, in a `dev` stage of its Dockerfile, so the prod image stays
  without them:

  | Tool | Image | Why there |
  |---|---|---|
  | ruff | loader | only the loader has Python code |
  | pytest, pytest-cov | loader | it imports the loader's code, so it needs the loader's libraries |
  | sqlfmt | dbt | built for dbt SQL (Jinja, `select` queries); the `Database` DDL is not formatted by any tool |
  | dbt Power User's dbt | dbt | the extension finds dbt in the container it runs in |

- **A new, unrelated project** gets its own compose with its own copies of these tools. Nothing is shared through
  Windows.
- **VS Code Dev Containers, one per image:** `.devcontainer/loader/devcontainer.json` and
  `.devcontainer/dbt/devcontainer.json`, each pointing to its compose service and its `dev` stage. Both mount the whole
  repo, so every file is visible from either; only the tools differ.
- **Claude Code stays on Windows**, outside the containers. One chat sees the whole repo and runs every tool through
  `docker compose run`, so it can do Python and dbt work in one go. Its login, memory and sessions stay in
  `%USERPROFILE%\.claude`.
- **Later, an on-prem server** changes only where the containers run: the dev window connects with Remote - SSH, and
  the same `devcontainer.json` files start the containers on the server. Then the ODBC DSN, Power BI and the VS Code
  connection point to the server instead of `localhost`, the input folders (`EXPORTS_DIR`, `CORRECTIONS_DIR`) must be
  reachable from the server, and Claude needs its own way to reach the server's Docker.

## Workflow from now on

Two VS Code windows on the same repo folder:

```
Window 1: the repo, opened locally on Windows    ← Claude Code panel lives here, never switches
Window 2: Dev Container (dbt or loader)          ← I work here, switch as often as I like
```

- **Window 1, Claude:** I ask, Claude edits the files on Windows and checks them by starting a short-lived container
  from the same images (`docker compose ... run --rm --entrypoint pytest loader`, ruff, sqlfmt, `dbt build`), or
  queries postgres with `docker exec dw-dev-postgres-1 psql ...`. Its edits show in window 2 right away, it is the same
  folder. Switching containers in window 2 does not touch it, so the chat keeps its context without `/resume`.
- **Window 2, me:** inside the container I run the tools directly (`dbt build`, `pytest`), and the extensions work
  (dbt Power User, the Testing panel, Python IntelliSense, Ruff).
- **A tool that is not in the current container** (pytest in the dbt container): Command Palette → **Dev Containers:
  Switch Container** → the other one. **Dev Containers: Reopen Folder Locally** goes back to Windows.
- Excel, Power BI and the VS Code PostgreSQL connection keep using `localhost:5432`, as now.

## Order of work

The tools get their new home before anything is deleted, so ruff, sqlfmt and pytest never stop working.

| # | What | Where | Status |
|---|---|---|---|
| a | `dev` stage in `docker/loader/Dockerfile` and `docker/dbt/Dockerfile` | git, this PC | Done |
| b | The two `devcontainer.json` files, and a mount of the whole repo | git, this PC | Done |
| c | Check the workflow above: both containers, both extensions, Claude's commands | each PC | Done on this PC |
| 1 | Delete the tracked files that are no longer needed | git, this PC | Done |
| 2 | Delete the untracked files that are no longer needed | each PC | Done on this PC |
| 3 | Uninstall from Windows what is no longer needed | each PC | Not started |

Steps a, b and 1 arrive on the other PC with `git pull`. Steps c, 2 and 3 are repeated there by hand, with the
sections below.

## Before starting on the other PC

- `.scratch/` and `.scripts/` are ignored by git, so a pull does not bring them and deleting them loses them. On this
  PC `.scratch/` holds only `metadata-in-meta-tables`; the test suite spec `.scratch/pipeline-test-suite/spec.md` that
  `CLAUDE.md` refers to, and `.scripts/rebuild.ps1`, are not here. Look for them on the other PC and keep them.
- Dev Containers cannot pass `--env-file`, so compose reads the root `.env`. Before step c, append the lines of
  `.env.dev` to the root `.env`, under its `POSTGRESQL_*` lines. In step 2 the `POSTGRESQL_*` lines go and `.env.dev` is
  deleted, so the root `.env` is the dev env file from then on. The commands in this file and in
  [DOCKER_IMPLEMENTATION.md](DOCKER_IMPLEMENTATION.md) already have no `--env-file .env.dev`.
- Dev Containers build their own Dockerfile from `%TEMP%` on top of the `dev` stage, and Compose v5's bake refuses to
  read a file outside the project folder ("additional privileges requested: pass --allow=fs.read=..."). Before step c,
  set the Windows user environment variable `BUILDX_BAKE_ENTITLEMENTS_FS=0`, then quit every VS Code window so the new
  value is picked up. It turns that check off for every build on the PC; remove it once Dev Containers pass the
  permission themselves. An env file does not work: only compose reads it, not the builder.
- Git for Windows sets `core.autocrlf=true` in its own config, which the git in the containers does not read, so there
  every file shows as modified (CRLF on disk, LF in git). Before step c, run `git config --local core.autocrlf true` in
  the repo: `.git/config` is in the shared folder, so both gits read it. It is not in git, so a pull does not bring it.

## Step c: check the workflow

Done on this PC on 2026-10-18. On the other PC, after the three items in "Before starting on the other PC":

1. **Open the loader container:** File → New Window, then Dev Containers: Open Folder in Container..., the repo
   folder, **loader**. VS Code does not open the same local folder in two windows, but a folder in a container counts
   as a different one. The bottom left says **Dev Container: loader**.
2. **Loader tools:** in its terminal, `ruff --version` and `pytest --collect-only -q | tail -n 1` (66 tests). The
   Testing panel lists the tests, and in `src/datawarehouse/databases/sql_postgres_database.py` Ruff underlines its
   known problems. Source Control shows the same changes as the Windows window.
3. **Switch to dbt:** Dev Containers: Switch Container, **dbt**. The loader container keeps running.
4. **dbt tools:** in its terminal, `sqlfmt --check DataWarehouseDbt/models DataWarehouseDbt/tests`, then
   `cd DataWarehouseDbt && dbt debug`. Open a model: the status bar shows dbt core with a check mark, and the Lineage
   view draws the graph.
5. **Claude's commands** (`docker compose ... run --rm`, `docker exec dw-dev-postgres-1 psql ...`) work while both
   containers run.

Known annoyance, accepted for now: compose compares the repo path as text, and Dev Containers use `c:\` where a
PowerShell prompt uses `C:\`, so opening or switching a container after a compose command from Windows (or the other
way round) recreates the postgres container. The data stays in its volume, but open connections (Excel, VS Code SQL
tabs) drop for a few seconds.

## Step 2: untracked files

Done on this PC on 2026-10-18. What arrived in git with it: `load_dotenv()`, `python-dotenv` and the defaults of every
setting are gone from the loader (a variable missing from `.env.loader` stops it with a `KeyError` naming it), and the
docs and comments name `.env` instead of `.env.dev`.

On the other PC, after `git pull`:

1. **Rebuild both containers:** Dev Containers: Rebuild Container, in the loader window and in the dbt window. The
   images lose `python-dotenv`, and the dbt container loses its separate `dbt_packages` volume. If Docker Desktop →
   **Volumes** then lists an anonymous volume (a long hash) that no container uses, delete it; never `dw-dev_pgdata`.
2. **The env files:** in the root `.env`, check that the lines under the `POSTGRESQL_*` block match `.env.dev`, then
   delete the `POSTGRESQL_*` lines and the two "temporary duplicate" comment lines, and put this first line:
   `# the dev compose env file. not in git. compose reads it by itself (and so do the Dev Containers), no --env-file needed`.
   Delete `.env.dev`. In `.env.loader` and `.env.transformer`, the comment "not POSTGRES_PORT from .env.dev" becomes
   "from .env". Check from PowerShell, in the repo root: `docker compose -f compose.yaml -f compose.dev.yaml --profile '*'
   config` shows `name: dw-dev` and no warning about a missing variable.
3. **Release the `.venv`:** in the Windows window, Extensions → dbt Power User → **Disable**. Its Python runs from
   `.venv\Scripts\pythonw.exe` and locks the folder. Task Manager must show no `pythonw.exe` from the repo.
4. **Delete**, in the repo:

   | Path | What it was |
   |---|---|
   | `.venv/` | the Windows Python, with dbt, ruff, pytest and sqlfmt |
   | `src/datawarehouse.egg-info/` | left by `pip install -e .` into the `.venv` |
   | every `__pycache__/` in `src` and `tests` | written by the Windows Python; the containers do not write them |
   | `.coverage`, `htmlcov/` | an old coverage report |
   | `logs/` in the repo root | dbt run from the repo root on Windows; the container logs to `DataWarehouseDbt/logs` |
   | `.pytest_cache/`, `.ruff_cache/` | caches; the loader container rebuilds them |
   | `.vs/` | Visual Studio's state, from the SSMS days |

5. **Keep:** `.env`, `.env.loader`, `.env.transformer`, `.scratch/`, `.scripts/`, and in `DataWarehouseDbt`:
   `dbt_packages/` (the dbt container uses it since the separate volume is gone), `target/`, `logs/`, `.user.yml`.

## Step 3: uninstall from Windows

To be written when step 3 is done.
