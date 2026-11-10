-- the published journal entries. no logic: staging has cast them. incremental, as every silver model (dbt_project.yml):
-- a row of the load replaces the row with the same date_time and device, so a newer upload of a measurement overrides
-- the older one. the key is unique_key in slvr_journal_entries.yml, next to the unique constraint it shares.
-- the ref_ models are not selected from, but silver must depend on them: dbt build skips silver after a failed test
-- only when every model that test reads is upstream of silver, so without these a failed relationship test lets the
-- load in
-- depends_on: {{ ref("ref_devices") }}
-- depends_on: {{ ref("ref_absolute_positions") }}
select * from {{ ref("stg_journal_entries") }}
