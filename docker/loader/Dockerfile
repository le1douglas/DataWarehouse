# the loader job: runs one load into the postgres service, then exits.
# built from the repo root (build context in compose.yaml), so paths below are relative to the repo root
FROM python:3.14-slim

# only what the loader needs, at the same versions as requirements.txt. no dbt: it has its own image
RUN pip install --no-cache-dir \
    pandas==3.0.6 \
    openpyxl==3.1.5 \
    pydantic==2.13.5 \
    SQLAlchemy==2.0.54 \
    "psycopg[binary]==3.3.6" \
    python-dotenv==1.2.3

WORKDIR /usr/app

# python finds the package in src without installing it, so in dev the mounted src is what runs.
# print output shows in the logs right away, and no __pycache__ is written into the mounted repo folder
ENV PYTHONPATH=/usr/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY src/ ./src/

# the container runs the package: "docker compose run --rm loader bronze" runs "python -m datawarehouse bronze"
ENTRYPOINT ["python", "-m", "datawarehouse"]
