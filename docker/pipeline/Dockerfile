# the pipeline: airflow, meltano and dbt. paths are relative to the repo root, the build context
# three stages (docs/DEV_CONTAINER.md):
# - venvs: airflow, dbt and meltano, each in its own venv. only their requirements files, so a change to a model or a
#   dag does not rebuild it
# - runtime: venvs plus the projects, the dbt packages and the meltano plugins. prod runs it, dev mounts the repo on top
# - dev: venvs plus the apps' venvs, the dev tools and psql. the dev container only

# the same base as the other images, so the meltano plugins' venvs find their python at the same path in dev
FROM python:3.14-slim AS venvs

# git: for dbt packages and meltano plugins installed from a git url
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# one venv each: airflow's constraints would otherwise force their versions on dbt and meltano
COPY docker/pipeline/requirements-airflow.txt /tmp/requirements/airflow.txt
COPY docker/pipeline/requirements-dbt.txt /tmp/requirements/dbt.txt
COPY docker/pipeline/requirements-meltano.txt /tmp/requirements/meltano.txt
RUN for venv in airflow dbt meltano; do \
        python -m venv /opt/venvs/$venv \
        && /opt/venvs/$venv/bin/pip install --no-cache-dir -r /tmp/requirements/$venv.txt || exit 1; \
    done \
    && rm -rf /tmp/requirements

# airflow, dbt and meltano from any folder, each with the python of its own venv
ENV PATH=/opt/venvs/airflow/bin:/opt/venvs/dbt/bin:/opt/venvs/meltano/bin:$PATH \
    AIRFLOW_HOME=/opt/airflow \
    DBT_PROJECT_DIR=/usr/app/DataWarehouseDbt \
    DBT_PROFILES_DIR=/usr/app/DataWarehouseDbt \
    MELTANO_PROJECT_ROOT=/usr/app/DataWarehouseMeltano \
    MELTANO_SEND_ANONYMOUS_USAGE_STATS=false \
    PYTHONUNBUFFERED=1

FROM venvs AS runtime

# at the paths the repo is mounted at in dev, so the mount hides them
COPY DataWarehouseDbt/ /usr/app/DataWarehouseDbt/
COPY DataWarehouseMeltano/ /usr/app/DataWarehouseMeltano/
COPY DataWarehouseAirflow/ /usr/app/DataWarehouseAirflow/

# - dbt parse checks the project, so a release that does not parse never becomes an image. it connects to nothing,
#   but the profile needs every env var: placeholders, for this command only
# - airflow's manifest is not this one: airflow-init writes it on every up
# - meltano install writes a sqlite system database without MELTANO_DATABASE_URI: removed, the container uses postgres
RUN dbt deps \
    && DBT_HOST=build DBT_PORT=0 DBT_DBNAME=build DBT_USER=build DBT_ENV_SECRET_PASSWORD=build TZ=Europe/Amsterdam \
        dbt parse \
    && meltano install \
    && rm /usr/app/DataWarehouseMeltano/.meltano/meltano.db

WORKDIR /usr/app

# compose gives the component, such as "scheduler" or "api-server"
ENTRYPOINT ["airflow"]

# dev: the dev container, from venvs, so airflow, dbt and meltano are runtime's exact build
# - not from runtime: the repo mount hides its projects, and a change to a model would rebuild this stage
# - node, Claude Code and pwsh come from the features of .devcontainer/dev/devcontainer.json
FROM venvs AS dev

# - libatomic1: node needs it, and the slim image lacks it
# - curl and ca-certificates: to fetch the signing key of postgresql's package source, below
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# psql, pg_dump and pg_restore at the server's major version, from postgresql's package source: debian has only 17
# - change together with the postgres image tag in docker/compose.yaml
RUN install -d /usr/share/postgresql-common/pgdg \
    && curl --fail -sSo /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && . /etc/os-release \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $VERSION_CODENAME-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-18 \
    && rm -rf /var/lib/apt/lists/*

# one venv per app, from its own requirements file, and one for the dev tools
# - pytest goes into the webapps venv, so it can import the web apps
COPY docker/webapps/requirements-webapps.txt /tmp/requirements/webapps.txt
COPY docker/pipeline/requirements-tools.txt /tmp/requirements/tools.txt
COPY docker/pipeline/requirements-pytest.txt /tmp/requirements/pytest.txt
RUN for venv in webapps tools; do \
        python -m venv /opt/venvs/$venv \
        && /opt/venvs/$venv/bin/pip install --no-cache-dir -r /tmp/requirements/$venv.txt || exit 1; \
    done \
    && /opt/venvs/webapps/bin/pip install --no-cache-dir -r /tmp/requirements/pytest.txt \
    && rm -rf /tmp/requirements

# webapps first, so "python" and "pytest" are the web apps'. each tool still runs with its own venv's python
ENV PATH=/opt/venvs/webapps/bin:/opt/venvs/tools/bin:$PATH

# - LANG: the slim image sets no locale, so psql, perl and less would fall back to ascii
# - PYTHONPATH: the packages in python/src run without being installed
# - no __pycache__ in the mounted repo
ENV LANG=C.UTF-8 \
    PYTHONPATH=/usr/app/python/src \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /usr/app

# nothing to run: the container stays up while the dev container is open
CMD ["sleep", "infinity"]
