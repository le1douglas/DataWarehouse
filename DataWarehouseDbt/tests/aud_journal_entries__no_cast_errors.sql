{{ config(severity="error", store_failures=true) }}

-- a cast error keeps its journal entry out of silver until the journal entry has a correction.
-- it selects from the candidate, so that dbt skips silver when it fails.
-- one row per journal entry, however many cast errors it has: their texts stay in meta_staging__failed_casts
select {{ failed_test_columns() }}
from {{ ref("cand_journal_entries") }} as candidate
where
    exists (
        select 1 from {{ ref("meta_staging__failed_casts") }} as failed_cast where failed_cast.row_id = candidate.row_id
    )
    -- a correction is trusted: any metadata in meta_corrections means the journal entry has one
    and not exists (
        select 1
        from {{ source("dev_corrections", "meta_corrections") }} as correction
        where correction.row_id = candidate.row_id
    )
