-- the published journal entries. no logic: staging has cast them, and holds only the latest load. it is added only
-- when its tests pass. a row of the load replaces the row with the same date_time and device, so a newer upload of a
-- measurement overrides the older one. full_refresh is off: a rebuild from staging would keep only the latest load.
-- the key is unique_key in slvr_journal_entries.yml, next to the unique constraint it shares.
-- the seeds are not selected from, but silver must depend on them: dbt build skips silver after a failed test only
-- when every model that test reads is upstream of silver, so without these a failed relationship test lets the load in
-- depends_on: {{ ref("seed_devices") }}
-- depends_on: {{ ref("seed_absolute_positions") }}
{{
    config(
        materialized="incremental",
        incremental_strategy="delete+insert",
        on_schema_change="fail",
        full_refresh=false,
    )
}}

select * from {{ ref("stg_journal_entries") }}
