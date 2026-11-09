# the dev image: every tool of the four runtime images, at the same versions, plus the dev tools, in one container.
# opened by the Dev Container in .devcontainer/dev, never used by prod.
# built from the repo root (build context in docker/compose.dev.yaml), so paths below are relative to the repo root.
# the same base as the runtime images, so python is the same build, and the meltano plugin venvs in the
# meltano-plugins volume (made by the meltano image) find their python at the same path
FROM python:3.14-slim

# git: dbt deps, meltano install of a plugin from a git url, and the source control panel.
# libatomic1: node needs it, and the slim image does not have it. node is installed by a feature of the Dev Container
# (.devcontainer/dev), for Claude Code's command line.
# curl and ca-certificates: to fetch the signing key of postgresql's own package source, below.
# the apt lists are removed after the install, so they do not stay in the image
RUN apt-get update \
    && apt-get install -y --no-install-recommends git libatomic1 curl ca-certificates \
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

# one venv per image, from that image's own requirements file: the same versions as the runtime image, and no clash
# between the libraries of dbt, meltano and nicegui. the dev tools in one more venv, from docker/dev
COPY docker/dbt/requirements.txt /tmp/requirements/dbt.txt
COPY docker/meltano/requirements.txt /tmp/requirements/meltano.txt
COPY docker/webapps/requirements.txt /tmp/requirements/webapps.txt
COPY docker/datastreamer/requirements.txt /tmp/requirements/datastreamer.txt
COPY docker/dev/requirements.txt /tmp/requirements/tools.txt
COPY docker/dev/requirements-test.txt /tmp/requirements/test.txt

# pytest goes into the webapps venv, so it can import them
RUN for venv in dbt meltano webapps datastreamer tools; do \
        python -m venv /opt/venvs/$venv \
        && /opt/venvs/$venv/bin/pip install --no-cache-dir -r /tmp/requirements/$venv.txt || exit 1; \
    done \
    && /opt/venvs/webapps/bin/pip install --no-cache-dir -r /tmp/requirements/test.txt \
    && rm -rf /tmp/requirements

# every command from any terminal. the webapps venv first, so "python" and "pytest" are the web apps' python.
# dbt, meltano and the tools each run with the python of their own venv, whatever comes first
ENV PATH=/opt/venvs/webapps/bin:/opt/venvs/tools/bin:/opt/venvs/dbt/bin:/opt/venvs/meltano/bin:/opt/venvs/datastreamer/bin:$PATH

# dbt and meltano find their project from any folder. python finds the packages in src without installing them, print
# output shows right away, and no __pycache__ is written into the mounted repo folder. no usage stats sent to meltano
# LANG: the slim image sets no locale, so programs other than python (psql, perl, less) fall back to ascii. C.UTF-8 is
# built into the image, nothing to install. the Dev Container keeps vs code's terminal from overriding it
# (terminal.integrated.detectLocale)
ENV LANG=C.UTF-8 \
    DBT_PROJECT_DIR=/usr/app/DataWarehouseDbt \
    DBT_PROFILES_DIR=/usr/app/DataWarehouseDbt \
    MELTANO_PROJECT_ROOT=/usr/app/DataWarehouseMeltano \
    MELTANO_SEND_ANONYMOUS_USAGE_STATS=false \
    PYTHONPATH=/usr/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# the repo is mounted here (docker/compose.dev.yaml)
WORKDIR /usr/app

# nothing to run: the container stays up for the Dev Container, for as long as it is open
CMD ["sleep", "infinity"]
