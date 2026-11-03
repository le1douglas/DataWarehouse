# the loader job: runs one load into the postgres service, then exits.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root
# runtime: only what the job needs to run. prod uses it as is, dev (and later ci) adds its own tools on top
FROM python:3.14-slim AS runtime

# git: dbt debug reports an error without it, as in the dbt image. the apt lists are removed after the install
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# only what the loader needs. dbt is the dbt image's: a load runs dbt build itself, to test the file, until an
# orchestrator does
RUN pip install --no-cache-dir \
    pandas==3.0.6 \
    pydantic==2.13.5 \
    SQLAlchemy==2.0.54 \
    "psycopg[binary]==3.3.6" \
    dbt-core==1.12.5 \
    dbt-postgres==1.11.0

WORKDIR /usr/app

# python finds the package in src without installing it, so in dev the mounted src is what runs.
# print output shows in the logs right away, and no __pycache__ is written into the mounted repo folder.
# dbt finds profiles.yml in the project, wherever it is run from
ENV PYTHONPATH=/usr/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DBT_PROFILES_DIR=/usr/app/DataWarehouseDbt

COPY src/ ./src/
COPY DataWarehouseDbt/ ./DataWarehouseDbt/

# installs dbt libraries at the version in package-lock.yml, as the dbt image does. needs no database connection
RUN cd DataWarehouseDbt && dbt deps

# the container runs the package: "docker compose run --rm loader bronze" runs "python -m datawarehouse bronze"
ENTRYPOINT ["python", "-m", "datawarehouse"]

# dev only (target: dev in docker/compose.dev.yaml): runtime plus the tools for the python code.
# their config is in pyproject.toml at the repo root
FROM runtime AS dev

RUN pip install --no-cache-dir \
    pytest==9.1.1 \
    pytest-cov==7.1.0 \
    ruff==0.16.10
