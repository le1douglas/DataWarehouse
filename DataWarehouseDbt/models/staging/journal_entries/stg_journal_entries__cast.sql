-- the staged journal entries with their types.
-- same column names and types as corrections
-- the columns, their order and their types are declared in stg_journal_entries.yml: a column with a guarded_cast is
-- cast,
-- the others are selected as they are. a value that cannot be cast becomes NULL and is reported in
-- meta_staging__failed_casts
select {{ guarded_casts("journal_entries") }} from {{ ref("stg_journal_entries") }}
