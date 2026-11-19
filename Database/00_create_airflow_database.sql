-- runs on the postgres container's first start, on an empty volume
-- by hand: psql -d postgres -v ON_ERROR_STOP=1 -f Database/00_create_airflow_database.sql
-- setup_common.ps1 also runs it on a volume older than airflow

-- airflow-init creates the tables. no transaction: CREATE DATABASE cannot run in one
CREATE DATABASE airflow;
