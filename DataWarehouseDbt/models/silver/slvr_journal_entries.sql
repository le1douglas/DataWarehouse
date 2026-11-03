-- the published journal entries. no logic: staging has cast them, and this is rebuilt only when its tests pass
select * from {{ ref("stg_journal_entries") }}
