
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
-- Creates only what dbt does not: the schemas and tables that python loads into.
-- dbt creates dev_staging, dev_candidate, dev_audit and dev_silver, and everything inside them.

CREATE SCHEMA IF NOT EXISTS dev_bronze;
CREATE SCHEMA IF NOT EXISTS dev_corrections;

-- raw data as provided by the source, all text. written by the python bronze loader.
CREATE TABLE IF NOT EXISTS dev_bronze.journal_entries (
    date_time              VARCHAR(50)  NOT NULL, -- key, together with subject
    subject                VARCHAR(50)  NOT NULL, -- key, together with date_time
    notes                  VARCHAR(400),   -- free text, can get long
    type                   VARCHAR(50),
    ec                     VARCHAR(50)  NOT NULL,
    ec_pore                VARCHAR(50),
    ec_bulk                VARCHAR(50),
    ph                     VARCHAR(50)  NOT NULL,
    mc                     VARCHAR(50),
    temp                   VARCHAR(50),
    device                 VARCHAR(50),
    media                  VARCHAR(50),
    tags                   VARCHAR(50),
    meta_extract_date_time TIMESTAMP    NOT NULL,
    meta_source            VARCHAR(400) NOT NULL -- path, can get long
);

-- the key: date_time cut to the second (first 19 characters of 2026-09-17T15:13:08.363212) plus subject
CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_entries_key
    ON dev_bronze.journal_entries (left(date_time, 19), subject);

-- manual corrections made in excel, typed like staging. written by the python corrections loader.
-- one row per key, the non-key columns override the staging values in the candidate view.
-- date_time is the bronze date_time as a timestamp cut to the second, without time zone, like in staging and candidate.
-- subject is the raw bronze value, the other columns have the same names as staging and silver.
CREATE TABLE IF NOT EXISTS dev_corrections.journal_entries (
    date_time               TIMESTAMP(0) NOT NULL, -- key, together with subject
    subject                 VARCHAR(50)  NOT NULL, -- key, together with date_time
    type                    VARCHAR(50),
    ml                      NUMERIC,
    ec                      NUMERIC,
    ph                      NUMERIC,
    temp                    NUMERIC,
    notes                   VARCHAR(400),
    room                    VARCHAR(50),
    meta_reviewed_by        VARCHAR(50)  NOT NULL,
    meta_reviewed_date_time TIMESTAMP    NOT NULL
);

-- same key as bronze, here date_time is already cut to the second
CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_entries_key
    ON dev_corrections.journal_entries (date_time, subject);

COMMIT;
