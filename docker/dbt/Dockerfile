# the dbt job: runs one dbt command against the postgres service, then exits.
# built from the repo root (build context in compose.yaml), so paths below are relative to the repo root
# runtime: only what the job needs to run. prod uses it as is, dev (and later ci) adds its own tools on top
FROM python:3.14-slim AS runtime

# git: dbt debug reports an error without it, and dbt deps needs it for packages installed from a git url.
# the apt lists are removed after the install, so they do not stay in the image
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# the same versions as requirements.txt
RUN pip install --no-cache-dir dbt-core==1.12.5 dbt-postgres==1.11.0

WORKDIR /usr/app/DataWarehouseDbt

# dbt finds profiles.yml here, wherever it is run from
ENV DBT_PROFILES_DIR=/usr/app/DataWarehouseDbt

COPY DataWarehouseDbt/ ./

# installs dbt_utils at the version in package-lock.yml. needs no database connection
RUN dbt deps

# the container runs dbt: "docker compose run dbt build" runs "dbt build", with no arguments it runs "dbt build"
ENTRYPOINT ["dbt"]
CMD ["build"]

# dev only (target: dev in compose.dev.yaml): runtime plus sqlfmt, at the same versions as requirements.txt.
# jinjafmt formats the jinja inside the sql with black. the config is in pyproject.toml at the repo root
FROM runtime AS dev

RUN pip install --no-cache-dir "shandy-sqlfmt[jinjafmt]==0.32.0" black==26.10.0
