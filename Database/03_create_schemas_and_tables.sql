
-- DO NOT RUN THIS DIRECTLY, instread from terminal run
-- psql -U postgres -h localhost -d DataWarehouse -1 -v ON_ERROR_STOP=1 -f Database\03_create_schemas_and_tables.sql
-- if you run from here you must also
-- ROLLBACK
-- after

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'DataWarehouse' THEN
        RAISE EXCEPTION 'Wrong database: connected to %, expected DataWarehouse', current_database();
    END IF;
END $$;
-- Creates only what dbt does not: the bronze schemas and tables.
-- dbt creates dev_silver, dev_gold, dev_experiments, prod_silver and prod_gold.
 
CREATE SCHEMA IF NOT EXISTS dev_bronze;
CREATE SCHEMA IF NOT EXISTS prod_bronze;
 
CREATE TABLE IF NOT EXISTS dev_bronze.journal_entries (
    date_time              VARCHAR(50), -- TODO primary key, but not unique, can have multiple entries for the same date_time
    subject                VARCHAR(50), -- TODO primary key, but not unique, subject is commonly shared.
    notes                  VARCHAR(400),   -- free text, can get long
    type                   VARCHAR(50),
    ec                     VARCHAR(50),
    ec_pore                VARCHAR(50),
    ec_bulk                VARCHAR(50),
    ph                     VARCHAR(50),
    mc                     VARCHAR(50),
    temp                   VARCHAR(50),
    device                 VARCHAR(50),
    media                  VARCHAR(50),
    tags                   VARCHAR(50),
    meta_extract_date_time TIMESTAMP    NOT NULL,
    meta_source            VARCHAR(400) NOT NULL -- path, can get long
);

-- create the same table in prod_bronze 
CREATE TABLE IF NOT EXISTS prod_bronze.journal_entries (LIKE dev_bronze.journal_entries INCLUDING ALL);

-- create btree index on prod_bronze date_time column
CREATE INDEX IF NOT EXISTS idx_journal_entries_date_time ON prod_bronze.journal_entries (date_time);
--drop index prod_bronze.idx_journal_entries_date_time;

--force execution with index scan, show the query plan
SET enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT ph FROM prod_bronze.journal_entries WHERE date_time >= '2026-09-17T15:09:00' AND date_time < '2026-09-17T15:13:00';
RESET enable_seqscan;


-- see indexes on the table
SELECT  *
FROM pg_indexes
WHERE schemaname = 'prod_bronze' AND tablename = 'journal_entries';


COMMIT;