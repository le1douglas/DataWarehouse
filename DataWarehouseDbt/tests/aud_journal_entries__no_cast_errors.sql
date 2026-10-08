{{ config(severity="error", store_failures=true) }}

select *
from {{ ref("cand_journal_entries") }}
where meta_cast_errors is not null
