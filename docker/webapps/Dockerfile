# the web apps: the NiceGUI pages of the warehouse, the home of the data collection programs, served on port 8080.
# built from the repo root (build context in docker/compose.yaml), so paths below are relative to the repo root
# runtime: only what it needs to run. prod uses it as is, dev mounts the repo on top (docker/compose.dev.yaml).
# the dev tools are not here: they are in the dev image, docker/dev/Dockerfile
FROM python:3.14-slim AS runtime

# only what the web apps need. the versions are in the requirements file, the one place they are written
# (docker/dev/Dockerfile reads it too)
COPY docker/webapps/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /usr/app

# python finds the webapps package in src without installing it, so in dev the mounted src is what runs.
# print output shows in the logs right away, and no __pycache__ is written into the mounted repo folder
ENV PYTHONPATH=/usr/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY src/webapps/ ./src/webapps/

# the container serves the web apps until it is stopped, on 0.0.0.0:8080 (the defaults of ui.run)
ENTRYPOINT ["python", "src/webapps/main.py"]
