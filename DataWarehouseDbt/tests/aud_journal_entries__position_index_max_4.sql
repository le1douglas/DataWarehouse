{{ config(severity="error", store_failures=true) }}

select {{ failed_test_columns() }}
from {{ ref("cand_journal_entries") }}
where position_index > 4
