-- Run by the postgres container on its first start on an empty volume (mounted into /docker-entrypoint-initdb.d).
-- DO NOT RUN THIS DIRECTLY. To run it by hand on an existing database, from terminal run
-- psql -U postgres -h localhost -d DataWarehouse -1 -v ON_ERROR_STOP=1 -f Database\01_create_schemas_and_tables.sql
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
-- Creates only what dbt does not: the schemas and tables that python loads into, with their meta tables.
-- dbt creates dw_staging, dw_candidate, dw_audit, dw_silver and dw_snapshots, and everything inside them.

CREATE SCHEMA IF NOT EXISTS dw_bronze;
CREATE SCHEMA IF NOT EXISTS dw_corrections;

-- raw data as provided by the source, all text. written by the python bronze loader.
-- row_id is the only key. it is assigned here, once, when the row is inserted: python does not send it.
-- it is unique across all datasets and follows the row unchanged through every layer.
CREATE TABLE IF NOT EXISTS dw_bronze.brnz_journal_entries (
    row_id UUID NOT NULL DEFAULT uuidv7(),
    date_time VARCHAR(100) NOT NULL, -- 57 with the longest time zone name: 2026-09-17T15:13:08.363212 America/North_Dakota/New_Salem
    subject VARCHAR(50) NOT NULL,
    notes VARCHAR(400),   -- free text, can get long
    type VARCHAR(50),
    ec VARCHAR(50) NOT NULL,
    ec_pore VARCHAR(50),
    ec_bulk VARCHAR(50),
    ph VARCHAR(50) NOT NULL,
    mc VARCHAR(50),
    temp VARCHAR(50),
    device VARCHAR(50),
    media VARCHAR(50),
    tags VARCHAR(50),
    CONSTRAINT pk_brnz_journal_entries PRIMARY KEY (row_id)
);

-- manual corrections made in excel, typed like staging. written by the python corrections loader.
-- one row per row_id, the other columns override the staging values in the candidate view.
-- row_id is the bronze row_id of the corrected row: it comes from the upload and is never generated here.
-- every column except row_id is text, like in staging: it is cast in silver, after the castable test on candidate,
-- so a correction that cannot be cast is reported by the test instead of refused by the load.
-- date_time is text with its time zone written, in the format of its source, like in staging and candidate
-- (2026-09-17T15:13:08.363212 Europe/Amsterdam). it is not checked here: a value that cannot be cast, or has no time
-- zone, is reported by the castable test.
-- the columns have the same names as staging and silver.
CREATE TABLE IF NOT EXISTS dw_corrections.corr_journal_entries (
    row_id UUID NOT NULL,
    date_time VARCHAR(100) NOT NULL, -- 57 with the longest time zone name: 2026-09-17T15:13:08.363212 America/North_Dakota/New_Salem
    subject VARCHAR(50) NOT NULL,
    type VARCHAR(50),
    ml VARCHAR(50),
    ec VARCHAR(50),
    ph VARCHAR(50),
    temp VARCHAR(50),
    notes VARCHAR(400),
    room_raw VARCHAR(50),
    CONSTRAINT pk_corr_journal_entries PRIMARY KEY (row_id),
    -- a correction is refused when its row_id is not a journal entry in bronze
    CONSTRAINT fk_corr_journal_entries_row_id FOREIGN KEY (row_id)
    REFERENCES dw_bronze.brnz_journal_entries (row_id)
);

-- the meta table of a layer holds the metadata recorded when its rows were loaded, for every dataset of that layer:
-- in bronze the source and the extract date-time, in corrections the reviewer and the review date-time.
-- the main tables above have no metadata columns.
-- one row is one fact about one row_id: kind says which fact (always starting with meta_), description holds its
-- value as text.
-- a fact is recorded only when there is something to say, so description is never null.
-- row_id is decided in bronze and carried through every layer, so every meta table references bronze.
-- only the two inputs have a meta table, both filled by python. the layers built by dbt have none.
-- a date-time kind ends in _date_time, and its description is a real date-time with its offset, as python writes it
-- (2026-10-22T14:42:08+02:00): metadata is never reviewed, so a value in another shape is refused by the load.
CREATE TABLE IF NOT EXISTS dw_bronze.meta_bronze (
    row_id UUID NOT NULL,
    kind VARCHAR(50) NOT NULL,
    description VARCHAR(400) NOT NULL,
    CONSTRAINT pk_meta_bronze PRIMARY KEY (row_id, kind),
    CONSTRAINT fk_meta_bronze_row_id FOREIGN KEY (row_id)
    REFERENCES dw_bronze.brnz_journal_entries (row_id),
    CONSTRAINT ck_meta_bronze_description CHECK (
        kind NOT LIKE '%\_date\_time'
        OR (description ~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$'
            AND pg_input_is_valid(description, 'timestamptz'))
    )
);

CREATE TABLE IF NOT EXISTS dw_corrections.meta_corrections (
    row_id UUID NOT NULL,
    kind VARCHAR(50) NOT NULL,
    description VARCHAR(400) NOT NULL,
    CONSTRAINT pk_meta_corrections PRIMARY KEY (row_id, kind),
    CONSTRAINT fk_meta_corrections_row_id FOREIGN KEY (row_id)
    REFERENCES dw_bronze.brnz_journal_entries (row_id),
    CONSTRAINT ck_meta_corrections_description CHECK (
        kind NOT LIKE '%\_date\_time'
        OR (description ~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$'
            AND pg_input_is_valid(description, 'timestamptz'))
    )
);

COMMIT;
