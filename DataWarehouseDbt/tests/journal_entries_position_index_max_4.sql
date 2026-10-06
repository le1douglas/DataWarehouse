{{ config(severity='error', store_failures=true) }}

select *
from {{ ref('journal_entries') }}
where position_index > 4