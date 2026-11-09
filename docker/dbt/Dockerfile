# the dbt job: runs one dbt command against the postgres service, then exits.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root
# runtime: only what the job needs to run. prod uses it as is, dev mounts the repo on top (docker/compose.dev.yaml).
# the dev tools are not here: they are in the dev image, docker/dev/Dockerfile
FROM python:3.14-slim AS runtime

# git: dbt debug reports an error without it, and dbt deps needs it for packages installed from a git url.
# the apt lists are removed after the install, so they do not stay in the image
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# the versions are in the requirements file, the one place they are written (docker/dev/Dockerfile reads it too)
COPY docker/dbt/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /usr/app/DataWarehouseDbt

# dbt finds profiles.yml here, wherever it is run from
ENV DBT_PROFILES_DIR=/usr/app/DataWarehouseDbt

COPY DataWarehouseDbt/ ./

# installs dbt libraries
RUN dbt deps

# the container runs dbt: "docker compose run dbt build" runs "dbt build", with no arguments it runs "dbt build"
ENTRYPOINT ["dbt"]
CMD ["build"]
