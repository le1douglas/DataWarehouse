-- runs on the postgres container's first start, on an empty volume
-- by hand: psql -d postgres -v ON_ERROR_STOP=1 -f Database/00_create_meltano_database.sql

-- meltano creates the tables. no transaction: CREATE DATABASE cannot run in one
CREATE DATABASE meltano;
