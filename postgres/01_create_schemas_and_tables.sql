-- runs on the postgres container's first start, on an empty volume
-- by hand: psql -v ON_ERROR_STOP=1 -f postgres/01_create_schemas_and_tables.sql
-- from an editor's SQL tab, a failure leaves the transaction open: run ROLLBACK
--
-- creates only what dbt does not:
-- - dw_bronze and its tables, which meltano loads into
-- - dw_control
-- dbt creates the other schemas and the staging views in dw_bronze

BEGIN;

-- run by hand, it would otherwise create the schemas in whatever database it is connected to
DO $$
BEGIN
    IF current_database() <> 'DataWarehouse' THEN
        RAISE EXCEPTION 'Wrong database: connected to %, expected DataWarehouse', current_database();
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS dw_bronze;

-- the data as the source sent it:
-- - all text and nullable: every rule is a dbt data test, which reports the row instead of failing the insert
-- - row_id is set here, since meltano does not send it
-- - load_id has no default, so a run without MELTANO_RUN_ID fails (meltano/meltano.yml)
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
    bench TEXT,
    remarks TEXT,
    reading_status TEXT,
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

-- the current state of each load (landed, accepted or refused, published or failed):
-- - written only by airflow (load_datasets.py), read by dbt
-- - no history: airflow's run history and bronze keep it
-- - no constraints: airflow inserts each load_id once
-- - source is the dataset
CREATE TABLE IF NOT EXISTS dw_control.ctl_loads (
    load_id UUID NOT NULL,
    source TEXT NOT NULL,
    state TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);



COMMIT;
