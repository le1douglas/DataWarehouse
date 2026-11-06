# Single dev container: test report and open items

Status on 2026-11-06: the dev container works, and nothing is committed yet.

- **Plan:** `C:\Users\TeeltQ-Farms\.claude\plans\yes-indedd-it-seems-steady-perlis.md`.
- **Reference:** `docs/agents/dev-container.md` (core, dev and prod; volumes; moving Claude's volume).

## What was tested

| Test | By | Result |
|---|---|---|
| Open the dev container, Claude Code login and memory | user | pass |
| Rebuild container, Claude keeps login and memory | user | pass, after adding `libatomic1` to the dev image (Node needs it) |
| dbt Power User: finds dbt, lineage, compiled preview | user | pass |
| Python extension: imports resolve, interpreter | user | pass, after removing `python-envs.defaultEnvManager` from `.vscode/settings.json` |
| YAML schema in `meltano.yml` | user | pass |
| Load: meltano run + dbt build | user and Claude in the container | pass: `PASS=37 WARN=1 ERROR=0` (the warning is the expected replacement) |
| Git panel the same in the container and on Windows | user | pass, after adding `.claude/settings.local.json` to `.gitignore` |
| Tools and versions match the requirements files | Claude in the container | pass |
| Interpreters and PATH per venv | Claude in the container | pass |
| Env vars (`CLAUDE_CONFIG_DIR`, `DBT_*_PATH`, `DBT_PROJECT_DIR`, `MELTANO_PROJECT_ROOT`) | Claude in the container | pass |
| Volumes: dbt-state, meltano-plugins, claude-config, exports read only, daily csv | Claude in the container | pass |
| dbt from any folder, packages in `/dbt-state` | Claude in the container | pass |
| No docker inside, postgres reachable | Claude in the container | pass |
| Git count | Claude in the container | 29, the same on both sides. The expected 30 was a mistake in the test |

## Open decisions (yours)

- [ ] **Format on save** for Python. Proposed for the `[python]` block of `.devcontainer/dev/devcontainer.json`:
      `editor.formatOnSave`, `source.fixAll.ruff`, `source.organizeImports.ruff`. Side effect: the first save of an
      unformatted file reformats all of it.
- [ ] **Commit:** one commit, or split (dbt-state / requirements files / dev container / docs).
- [ ] **dbt-core 1.12.6** is out, and the pin is 1.12.5. Bump it or not (`docker/dbt/requirements.txt`).

## To do (small)

- [ ] **Remove the old dev container and recreate the web apps** on the runtime image. From PowerShell at the repo root:
      `docker rm -f dw-dev-dbt-1`, then
      `docker compose -f docker/compose.yaml -f docker/compose.dev.yaml up -d --no-deps --build webapps`. Check that
      http://localhost:8080 still serves and reloads on save.
- [ ] **Re-install the Claude plugins** (mattpocock skills) inside the container: they were not copied, because their
      install records hold Windows paths.
- [ ] **Rename the memory file** `use-running-loader-container.md` (its slug is outdated, its title says "Use the dev
      container"), in the `claude-config` volume.
- [x] `docs/agents/dev-container.md` said `/dumps` is in the dev container. It's on postgres. Fixed.

## Later / separate issues

- **Lockfile per image:** a rebuild resolved newer transitive versions than the old images had (pydantic, and
  SQLAlchemy under meltano). The top-level pins are unchanged. A lockfile would prevent this, and CI would catch it.
- **Existing lint and format findings,** not caused by this change:
  - ruff: 2× E501;
  - ruff format: 2 files (`docs/NICEGUI_STANDARDS.md`, `src/bluelab_datastreamer/onepen.py`);
  - sqlfmt: 5 files, including `fct_journal_entries.sql`, `slvr_journal_entries.sql`, `unique_across_accepted_uploads.sql`
    and `unique_within_upload.sql`.
- **dbt warning:** `ec`, `ph` and `temperature` are `numeric` without precision or scale in silver and gold, which can
  round values.
- **No `psql` in the dev container:** a load id comes from a one-line Python call for now.

## Noted, no action needed

- **PATH lists each venv three times,** with nvm in front. The Dev Containers environment probe adds it again, and it
  does no harm.
- **The `webapps` hostname resolves in the dev network.** That's normal for one compose project.
- **`tap-csv v1.2.0` in the meltano log:** the installed plugin is the `v1.3.2` tag (commit `0c84ec0`). Upstream didn't
  update its version number at that tag.
- **Test logs in the container:** `/tmp/claude-0/meltano.log` and `build.log`. They go away with the next rebuild.
