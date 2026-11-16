# the pipeline: runs every load, airflow with meltano and dbt, the two of them in this image. compose starts one container per
# airflow component (api server, scheduler, dag processor), each with its own command.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root.
# three stages (docs/DEV_CONTAINER.md):
# - venvs: the tools, airflow, dbt and meltano, each in its own venv, with the env vars they read. nothing of the repo
#   but their requirements files, so a change to a model or a dag does not rebuild it
# - runtime: venvs, plus the projects, the dags, the dbt packages and manifest and the meltano plugins. what compose
#   builds (target: runtime): prod uses it as is, dev mounts the repo on top (docker/compose.dev.yaml)
# - dev: venvs, plus the venvs of the apps, the dev tools and psql. the dev container (target: dev in
#   docker/compose.dev.yaml), never used by prod

# venvs: the same base as the other images, so the meltano plugin venvs find their python at the same path in dev
FROM python:3.14-slim AS venvs

# git: dbt deps for packages from a git url, meltano install of a plugin whose pip_url is a git url.
# the apt lists are removed after the install, so they do not stay in the image
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# one venv each: airflow's constraints would otherwise force their versions on dbt and
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

# dev: the dev container (.devcontainer/dev), never used by prod. venvs, so airflow, dbt and meltano are the exact build
# of runtime, plus the venvs of the apps, the dev tools and psql. not runtime: the projects baked there are hidden by the
# repo mount anyway, and a change to a model would rebuild this stage. no ENTRYPOINT: it is set in runtime only.
# node, Claude Code and pwsh are not here: the features of .devcontainer/dev/devcontainer.json add them
FROM venvs AS dev

# libatomic1: node needs it, and the slim image does not have it (node comes from a feature of the Dev Container).
# curl and ca-certificates: to fetch the signing key of postgresql's own package source, below. git is in venvs.
# the apt lists are removed after the install, so they do not stay in the image
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# psql, pg_dump and pg_restore, at the major version of the server. debian has only its own major (17), so they come
# from postgresql's own package source, the one the postgres image installs the server from.
# the major version is written twice: here and in the postgres image tag in docker/compose.yaml. change both together;
# psql warns when its major differs from the server's. the minor version is the newest at build, as the server's is
RUN install -d /usr/share/postgresql-common/pgdg \
    && curl --fail -sSo /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $VERSION_CODENAME-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-18 \
    && rm -rf /var/lib/apt/lists/*

# one venv per app, from the apps' own requirements files, so dev runs their versions, and the dev tools in one more.
# pytest goes into the webapps venv, so it can import the web apps
COPY docker/webapps/requirements.txt /tmp/requirements/webapps.txt
COPY docker/datastreamer/requirements.txt /tmp/requirements/datastreamer.txt
COPY docker/pipeline/requirements-tools.txt /tmp/requirements/tools.txt
COPY docker/pipeline/requirements-test.txt /tmp/requirements/test.txt
RUN for venv in webapps datastreamer tools; do \
        python -m venv /opt/venvs/$venv \
        && /opt/venvs/$venv/bin/pip install --no-cache-dir -r /tmp/requirements/$venv.txt || exit 1; \
    done \
    && /opt/venvs/webapps/bin/pip install --no-cache-dir -r /tmp/requirements/test.txt \
    && rm -rf /tmp/requirements

# every command from any terminal. the webapps venv first, so "python" and "pytest" are the web apps' python, then the
# tools and the datastreamer, then the airflow, dbt and meltano of venvs ($PATH). each tool runs with the python of its
# own venv, whatever comes first
ENV PATH=/opt/venvs/webapps/bin:/opt/venvs/tools/bin:/opt/venvs/datastreamer/bin:$PATH

# python finds the packages in src without installing them, and writes no __pycache__ into the mounted repo folder.
# LANG: the slim image sets no locale, so programs other than python (psql, perl, less) fall back to ascii. C.UTF-8 is
# built into the image, nothing to install. the Dev Container keeps vs code's terminal from overriding it
# (terminal.integrated.detectLocale). the env vars of airflow, dbt and meltano come from venvs
ENV LANG=C.UTF-8 \
    PYTHONPATH=/usr/app/src \
    PYTHONDONTWRITEBYTECODE=1

# the repo is mounted here (docker/compose.dev.yaml)
WORKDIR /usr/app

# nothing to run: the container stays up for the Dev Container, for as long as it is open
CMD ["sleep", "infinity"]
