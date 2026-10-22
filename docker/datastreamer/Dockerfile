# the datastreamer: the drip and drain readings of the OnePen, taken on the terminal, until q.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root
# runtime: only what it needs to run. prod uses it as is, dev (and later ci) adds its own tools on top
FROM python:3.14-slim AS runtime

# no libraries: the readings use only the standard library. the bridge to the pen (onepen_bridge.py), which
# needs bleak, runs on windows, where the bluetooth adapter is, and is not in this image

WORKDIR /usr/app

# print output shows right away, and no __pycache__ is written into the mounted repo folder
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY src/bluelab_datastreamer/ ./src/bluelab_datastreamer/

# "docker compose run --rm datastreamer" takes the readings. the csv of the readings is written next to the code,
# in src/bluelab_datastreamer: without the repo mounted (dev), it is lost with the container
ENTRYPOINT ["python", "src/bluelab_datastreamer/drip_drain_cli.py"]

# dev only (target: dev in docker/compose.dev.yaml): runtime plus the tools for the python code.
# their config is in pyproject.toml at the repo root
FROM runtime AS dev

# git: the source control panel of the dev container runs git inside it. the apt lists are removed after the install
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ruff==0.16.10
