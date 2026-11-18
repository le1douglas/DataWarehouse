-- Run by the postgres container on its first start on an empty volume (mounted into /docker-entrypoint-initdb.d),
-- before 01_create_schemas_and_tables.sql. To run it by hand on an existing server, from the dev container run
-- psql -d postgres -v ON_ERROR_STOP=1 -f Database/00_create_airflow_database.sql

-- airflow's metadata database (its dags, runs, task states and history), next to DataWarehouse on the same server.
-- empty: airflow db migrate (the airflow-init service) creates and migrates its tables. not in a transaction,
-- CREATE DATABASE cannot run in one
CREATE DATABASE airflow;
