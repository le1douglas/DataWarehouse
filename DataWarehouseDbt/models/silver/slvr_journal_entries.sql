-- the published journal entries. no logic: staging has cast them, and holds only the latest load. it is added only
-- when its tests pass. a row of the load replaces the row with the same date_time and device, so a newer upload of a
-- measurement overrides the older one. full_refresh is off: a rebuild from staging would keep only the latest load.
-- the key is unique_key in slvr_journal_entries.yml, next to the unique constraint it shares
{{
    config(
        materialized="incremental",
        incremental_strategy="delete+insert",
        on_schema_change="fail",
        full_refresh=false,
    )
}}

select * from {{ ref("stg_journal_entries") }}
