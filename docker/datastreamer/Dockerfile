# the datastreamer: the drip and drain readings of the OnePen, taken on the terminal, until q.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root
# runtime: only what it needs to run. prod uses it as is, dev mounts the repo on top (docker/compose.dev.yaml).
# the dev tools are not here: they are in the dev image, docker/dev/Dockerfile
FROM python:3.14-slim AS runtime

# the libraries, from the requirements file, the one place their versions are written (docker/dev/Dockerfile reads
# it too). none for now: the readings use only the standard library. the bridge to the pen (onepen_bridge.py), which
# needs bleak, runs on windows, where the bluetooth adapter is, and is not in this image
COPY docker/datastreamer/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /usr/app

# print output shows right away, and no __pycache__ is written into the mounted repo folder
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY src/bluelab_datastreamer/ ./src/bluelab_datastreamer/

# "docker compose run --rm datastreamer" takes the readings. the csv of the rooms done so far is in the work-in-progress
# volume (docker/compose.yaml), so it outlives the container
ENTRYPOINT ["python", "src/bluelab_datastreamer/drip_drain_cli.py"]
