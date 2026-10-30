# the web apps: the NiceGUI pages of the warehouse (for now the corrections), served on port 8080.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root
# runtime: only what it needs to run. prod uses it as is, dev (and later ci) adds its own tools on top
FROM python:3.14-slim AS runtime

# git: dbt debug reports an error without it, as in the dbt image. the apt lists are removed after the install
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# only what the web apps need. the database libraries are the loader's versions, dbt is the dbt image's: the submit
# runs dbt build itself, until an orchestrator does
RUN pip install --no-cache-dir \
    nicegui==3.18.0 \
    SQLAlchemy==2.0.54 \
    "psycopg[binary]==3.3.6" \
    dbt-core==1.12.5 \
    dbt-postgres==1.11.0

WORKDIR /usr/app

# python finds the webapps package in src without installing it, so in dev the mounted src is what runs (as the loader).
# print output shows in the logs right away, and no __pycache__ is written into the mounted repo folder.
# dbt finds profiles.yml in the project, wherever it is run from
ENV PYTHONPATH=/usr/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DBT_PROFILES_DIR=/usr/app/DataWarehouseDbt

COPY src/webapps/ ./src/webapps/
COPY DataWarehouseDbt/ ./DataWarehouseDbt/

# installs dbt_utils at the version in package-lock.yml, as the dbt image does. needs no database connection
RUN cd DataWarehouseDbt && dbt deps

# the container serves the web apps until it is stopped, on 0.0.0.0:8080 (the defaults of ui.run)
ENTRYPOINT ["python", "src/webapps/main.py"]

# dev only (target: dev in docker/compose.dev.yaml): runtime plus the tools for the python code.
# their config is in pyproject.toml at the repo root
FROM runtime AS dev

# git: the source control panel of the dev container runs git inside it. the apt lists are removed after the install
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ruff==0.16.10
