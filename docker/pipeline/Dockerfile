# the pipeline: runs every load, airflow with meltano and dbt, the two of them in this image. compose starts one container per
# airflow component (api server, scheduler, dag processor), each with its own command.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root.
# two stages (docs/DEV_CONTAINER.md):
# - venvs: the tools, airflow, dbt and meltano, each in its own venv, with the env vars they read. nothing of the repo
#   but their requirements files, so a change to a model or a dag does not rebuild it
# - runtime: venvs, plus the projects, the dags, the dbt packages and manifest and the meltano plugins. what compose
#   builds (target: runtime): prod uses it as is, dev mounts the repo on top (docker/compose.dev.yaml)

# venvs: the same base as the other images, so the meltano plugin venvs find their python at the same path in dev
FROM python:3.14-slim AS venvs

# git: dbt deps for packages from a git url, meltano install of a plugin whose pip_url is a git url.
# the apt lists are removed after the install, so they do not stay in the image
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# one venv each, as in docker/dev/Dockerfile: airflow's constraints would otherwise force their versions on dbt and
# meltano. the versions are in each requirements file, the one place they are written
COPY docker/pipeline/requirements.txt /tmp/requirements/airflow.txt
COPY docker/pipeline/requirements-dbt.txt /tmp/requirements/dbt.txt
COPY docker/pipeline/requirements-meltano.txt /tmp/requirements/meltano.txt
RUN for venv in airflow dbt meltano; do \
        python -m venv /opt/venvs/$venv \
        && /opt/venvs/$venv/bin/pip install --no-cache-dir -r /tmp/requirements/$venv.txt || exit 1; \
    done \
    && rm -rf /tmp/requirements

# airflow, dbt and meltano from any folder, each with the python of its own venv.
# airflow keeps its config and logs in AIRFLOW_HOME. dbt and meltano find their project from any folder.
# no usage stats sent to meltano. print output shows in the logs right away
ENV PATH=/opt/venvs/airflow/bin:/opt/venvs/dbt/bin:/opt/venvs/meltano/bin:$PATH \
    AIRFLOW_HOME=/opt/airflow \
    DBT_PROJECT_DIR=/usr/app/DataWarehouseDbt \
    DBT_PROFILES_DIR=/usr/app/DataWarehouseDbt \
    MELTANO_PROJECT_ROOT=/usr/app/DataWarehouseMeltano \
    MELTANO_SEND_ANONYMOUS_USAGE_STATS=false \
    PYTHONUNBUFFERED=1

# runtime: the tools of venvs with what they run on
FROM venvs AS runtime

# the projects and the dags at the same paths as in the dev container, so the repo mounted at /usr/app in dev hides
# them. the dags folder is AIRFLOW__CORE__DAGS_FOLDER in docker/compose.yaml
COPY DataWarehouseDbt/ /usr/app/DataWarehouseDbt/
COPY DataWarehouseMeltano/ /usr/app/DataWarehouseMeltano/
COPY DataWarehouseAirflow/ /usr/app/DataWarehouseAirflow/

# the dbt libraries, and the meltano plugins at the version pinned in meltano.yml, into .meltano/.
# meltano install needs no database connection: without MELTANO_DATABASE_URI at build time it writes a sqlite system
# database, removed after, as the container uses postgres.
# dbt parse writes target/manifest.json, which cosmos draws the dbt tasks from (DataWarehouseAirflow/dags/utils/
# dbt_task_group.py). it connects to nothing, but the profile and the project read env vars: placeholders, for this
# command only, so none of them stays in the image
RUN dbt deps \
    && DBT_HOST=build DBT_PORT=0 DBT_DBNAME=build DBT_USER=build DBT_ENV_SECRET_PASSWORD=build TZ=Europe/Amsterdam \
        dbt parse \
    && meltano install \
    && rm /usr/app/DataWarehouseMeltano/.meltano/meltano.db

WORKDIR /usr/app

# the container runs airflow: compose gives the component, such as "scheduler" or "api-server"
ENTRYPOINT ["airflow"]
