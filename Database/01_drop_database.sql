-- run while connected to the postgres database. WITH (FORCE) disconnects every session on DataWarehouse.
DROP DATABASE IF EXISTS "DataWarehouse" WITH (FORCE);
