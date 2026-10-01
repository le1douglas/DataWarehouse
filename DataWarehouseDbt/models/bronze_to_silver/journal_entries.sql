
select *
from {{ source('bronze', 'journal_entries') }}
