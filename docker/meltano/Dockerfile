# the meltano job: runs one meltano command, then exits.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root
# runtime: only what the job needs to run. prod uses it as is, dev mounts the repo on top (docker/compose.dev.yaml)
FROM python:3.14-slim AS runtime

# git: meltano installs plugins whose pip_url is a git url. the apt lists are removed after the install
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# the versions are in the requirements file, the one place they are written (docker/dev/Dockerfile reads it too)
COPY docker/meltano/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /usr/app/DataWarehouseMeltano

# no usage stats sent to meltano
ENV MELTANO_SEND_ANONYMOUS_USAGE_STATS=false

COPY DataWarehouseMeltano/ ./

# installs the plugins at the version pinned in meltano.yml, into .meltano/, as dbt deps does in the dbt image.
# needs no database connection: without MELTANO_DATABASE_URI at build time meltano writes a sqlite system database,
# removed after, as the container uses postgres
RUN meltano install && rm .meltano/meltano.db

# the container runs meltano: "docker compose run --rm meltano run tap-x target-y" runs "meltano run tap-x target-y"
ENTRYPOINT ["meltano"]
