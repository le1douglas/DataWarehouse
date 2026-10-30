# the loader job: runs one load into the postgres service, then exits.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root
# runtime: only what the job needs to run. prod uses it as is, dev (and later ci) adds its own tools on top
FROM python:3.14-slim AS runtime

# only what the loader needs. no dbt: it has its own image
RUN pip install --no-cache-dir \
    pandas==3.0.6 \
    pydantic==2.13.5 \
    SQLAlchemy==2.0.54 \
    "psycopg[binary]==3.3.6"

WORKDIR /usr/app

# python finds the package in src without installing it, so in dev the mounted src is what runs.
# print output shows in the logs right away, and no __pycache__ is written into the mounted repo folder
ENV PYTHONPATH=/usr/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY src/ ./src/

# the container runs the package: "docker compose run --rm loader bronze" runs "python -m datawarehouse bronze"
ENTRYPOINT ["python", "-m", "datawarehouse"]

# dev only (target: dev in docker/compose.dev.yaml): runtime plus the tools for the python code.
# their config is in pyproject.toml at the repo root
FROM runtime AS dev

# git: the source control panel of the dev container runs git inside it. the apt lists are removed after the install
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pytest==9.1.1 \
    pytest-cov==7.1.0 \
    ruff==0.16.10
