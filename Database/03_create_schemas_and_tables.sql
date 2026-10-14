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
-- Creates only what dbt does not: the schemas and tables that python loads into, with their meta tables.
-- dbt creates dev_staging, dev_candidate, dev_audit and dev_silver, and everything inside them.

CREATE SCHEMA IF NOT EXISTS dev_bronze;
CREATE SCHEMA IF NOT EXISTS dev_corrections;

-- raw data as provided by the source, all text. written by the python bronze loader.
-- row_id is the only key. it is assigned here, once, when the row is inserted: python does not send it.
-- it is unique across all datasets and follows the row unchanged through every layer.
CREATE TABLE IF NOT EXISTS dev_bronze.brnz_journal_entries (
    row_id UUID NOT NULL DEFAULT uuidv7(),
    date_time VARCHAR(50) NOT NULL,
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
-- date_time is a timestamp cut to the second, without time zone, like in staging and candidate.
-- the measurements are text, like in staging: they are cast in silver, after the castable test on candidate,
-- so a correction that is not a number is reported by the test instead of refused by the load.
-- the columns have the same names as staging and silver.
CREATE TABLE IF NOT EXISTS dev_corrections.corr_journal_entries (
    row_id UUID NOT NULL,
    date_time TIMESTAMP(0) NOT NULL,
    subject VARCHAR(50) NOT NULL,
    type VARCHAR(50),
    ml VARCHAR(50),
    ec VARCHAR(50),
    ph VARCHAR(50),
    temp VARCHAR(50),
    notes VARCHAR(400),
    room VARCHAR(50),
    CONSTRAINT pk_corr_journal_entries PRIMARY KEY (row_id),
    -- a correction is refused when its row_id is not a journal entry in bronze
    CONSTRAINT fk_corr_journal_entries_row_id FOREIGN KEY (row_id)
    REFERENCES dev_bronze.brnz_journal_entries (row_id)
);

-- the meta table of a layer holds the metadata that the layer decided, for every dataset of that layer.
-- the main tables above have no metadata columns.
-- one row is one fact about one row_id: kind says which fact, description holds its value as text.
-- a fact is recorded only when there is something to say, so description is never null.
-- row_id is decided in bronze and carried through every layer, so every meta table references bronze.
-- only the two inputs have a meta table, both filled by python. the layers built by dbt have none.
CREATE TABLE IF NOT EXISTS dev_bronze.meta_bronze (
    row_id UUID NOT NULL,
    kind VARCHAR(50) NOT NULL,
    description VARCHAR(400) NOT NULL,
    CONSTRAINT pk_meta_bronze PRIMARY KEY (row_id, kind),
    CONSTRAINT fk_meta_bronze_row_id FOREIGN KEY (row_id)
    REFERENCES dev_bronze.brnz_journal_entries (row_id)
);

CREATE TABLE IF NOT EXISTS dev_corrections.meta_corrections (
    row_id UUID NOT NULL,
    kind VARCHAR(50) NOT NULL,
    description VARCHAR(400) NOT NULL,
    CONSTRAINT pk_meta_corrections PRIMARY KEY (row_id, kind),
    CONSTRAINT fk_meta_corrections_row_id FOREIGN KEY (row_id)
    REFERENCES dev_bronze.brnz_journal_entries (row_id)
);

COMMIT;
