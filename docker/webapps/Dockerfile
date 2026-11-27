# the web apps: the NiceGUI pages of the warehouse. paths are relative to the repo root, the build context
# - prod runs it, dev mounts the repo on top. the dev tools are in the dev container
FROM python:3.14-slim AS runtime

COPY docker/webapps/requirements-webapps.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /usr/app

# - PYTHONPATH: the package in python/src runs without being installed, so in dev the mounted code runs
# - no __pycache__ in the mounted repo
ENV PYTHONPATH=/usr/app/python/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY python/src/webapps/ ./python/src/webapps/

# serves on 0.0.0.0:8080, ui.run's defaults
ENTRYPOINT ["python", "python/src/webapps/main.py"]
