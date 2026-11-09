-- Run by the postgres container on its first start on an empty volume (mounted into /docker-entrypoint-initdb.d),
-- before 01_create_schemas_and_tables.sql. To run it by hand on an existing server, from terminal run
-- psql -U postgres -h localhost -d postgres -v ON_ERROR_STOP=1 -f Database\00_create_meltano_database.sql

-- meltano's system database (its own state and run history), next to DataWarehouse on the same server.
-- empty: meltano creates and migrates its tables itself. not in a transaction, CREATE DATABASE cannot run in one
CREATE DATABASE meltano;
