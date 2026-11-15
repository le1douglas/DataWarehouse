-- Run by the postgres container on its first start on an empty volume (mounted into /docker-entrypoint-initdb.d),
-- after 01_create_schemas_and_tables.sql. To run it by hand on an existing server, from terminal run
-- psql -U postgres -h localhost -d postgres -v ON_ERROR_STOP=1 -f Database\02_create_openmetadata_database.sql

-- OpenMetadata's own database (its catalog: entities, descriptions, owners, glossary), next to DataWarehouse and
-- meltano on the same server. empty: its migration job creates and migrates the tables itself. owned by postgres
-- until the roles exist. not in a transaction, CREATE DATABASE cannot run in one
CREATE DATABASE openmetadata;
