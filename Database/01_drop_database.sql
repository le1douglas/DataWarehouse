DROP DATABASE "DataWarehouse" WITH (FORCE);

--psql -U postgres -h localhost -d postgres -v ON_ERROR_STOP=1 -f Database\01_drop_database.sql -f Database\02_create_database.sql; if ($LASTEXITCODE -eq 0) { psql -U postgres -h localhost -d DataWarehouse -1 -v ON_ERROR_STOP=1 -f Database\03_create_schemas_and_tables.sql }
