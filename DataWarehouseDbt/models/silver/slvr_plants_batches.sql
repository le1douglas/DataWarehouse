{{ config(unique_key=["pp_number"]) }}

-- the published plants batches. no logic: staging has cast them, and its yml declares the columns and types that
-- select * passes on. incremental, as every silver model (dbt_project.yml): a row of the load replaces the row with
-- the same pp_number, so a newer upload of a plants batch overrides the older one. unique_key is declared only here:
-- the staging uniqueness tests and silver's index on it (unique_key_index) read it from this config.
-- the ref_ model is not selected from, but silver must depend on it: dbt build skips silver after a failed test only
-- when every model that test reads is upstream of silver, so without this a failed relationship test lets the load in
-- depends_on: {{ ref("ref_rooms") }}
select *
from {{ ref("stg_plants_batches") }}
