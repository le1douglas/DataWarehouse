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
-- Creates only what dbt does not: the schema and tables that meltano loads into.
-- dbt creates dw_silver, dw_seeds and dw_gold, and everything inside them, and the staging views in dw_bronze.

CREATE SCHEMA IF NOT EXISTS dw_bronze;

-- raw data as provided by the source, all text and nullable: every rule on the data is a dbt data test, so a bad value
-- is reported with its row instead of refused by the load. written by meltano (target-postgres).
-- row_id is the only key. it is assigned here, once, when the row is inserted: meltano does not send it.
-- it is unique across all datasets and follows the row unchanged through every layer.
-- load_id is the upload the row came in with: meltano's run_id, which the caller sets with MELTANO_RUN_ID and meltano
-- writes onto every row (DataWarehouseMeltano/meltano.yml). no default: a run started without it is refused here
CREATE TABLE IF NOT EXISTS dw_bronze.brnz_journal_entries (
    row_id UUID NOT NULL DEFAULT uuidv7(),
    load_id UUID NOT NULL,
    date_time TEXT,
    device TEXT,
    spot TEXT,
    ml TEXT,
    ec TEXT,
    ph TEXT,
    temperature TEXT,
    room TEXT,
    CONSTRAINT pk_brnz_journal_entries PRIMARY KEY (row_id)
);


CREATE TABLE IF NOT EXISTS dw_bronze.brnz_plants_batches (
    row_id UUID NOT NULL DEFAULT uuidv7(),
    load_id UUID NOT NULL,
    room TEXT,
    strain TEXT,
    pp_number TEXT,
    date_veg_start TEXT,
    date_flower_start TEXT,
    date_flower_end TEXT,
    plants_number TEXT,
    CONSTRAINT pk_brnz_plants_batches PRIMARY KEY (row_id)
);


CREATE SCHEMA IF NOT EXISTS dw_control;

-- the current state of every load, one row per load, written only by airflow
-- (DataWarehouseAirflow/dags/load_datasets.py) and read by dbt to choose the load staging holds and silver publishes.
-- inserted when the load is landed, then updated in place: accepted or refused, then published or failed
-- (docs/ARCHITECTURE_PROPOSAL.md, SIMPLIFIED IMPLEMENTATION).
-- the path a load took is in airflow's run history, its rows in bronze. source is the dataset the load belongs to
-- (journal_entries). no key and no check: only airflow writes it, inserting a load_id once.
-- updated_at is when state last changed
CREATE TABLE IF NOT EXISTS dw_control.ctl_loads (
    load_id UUID NOT NULL,
    source TEXT NOT NULL,
    state TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);



COMMIT;
