# the datastreamer: the drip and drain readings of the OnePen. paths are relative to the repo root, the build context
# - prod runs it, dev mounts the repo on top. the dev tools are in the dev container
FROM python:3.14-slim AS runtime

COPY docker/datastreamer/requirements-datastreamer.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /usr/app

# no __pycache__ in the mounted repo
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY src/bluelab_datastreamer/ ./src/bluelab_datastreamer/

ENTRYPOINT ["python", "src/bluelab_datastreamer/drip_drain_cli.py"]
