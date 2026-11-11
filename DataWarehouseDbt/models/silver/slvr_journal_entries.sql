
-- the published journal entries. no logic: staging has cast them, and its yml declares the columns and types that
-- select * passes on. incremental, as every silver model (dbt_project.yml): a row of the load replaces the row with
-- the same date_time and device, so a newer upload of a measurement overrides the older one. unique_key is declared
-- only here: the staging uniqueness tests and silver's index on it (unique_key_index) read it from this config.
-- the ref_ models are not selected from, but silver must depend on them: dbt build skips silver after a failed test
-- only when every model that test reads is upstream of silver, so without these a failed relationship test lets the
-- load in
-- depends_on: {{ ref("ref_devices") }}
-- depends_on: {{ ref("ref_absolute_positions") }}

{{ config(unique_key=["date_time", "device"]) }}
select *
from {{ ref("stg_journal_entries") }}
