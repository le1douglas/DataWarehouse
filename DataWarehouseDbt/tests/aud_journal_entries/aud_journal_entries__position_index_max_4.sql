-- the error is in the whole row, not in one column, so target_column is null
select row_id, null::text as target_column, 'more than 4 positions for this room' as description
from {{ ref("cand_journal_entries") }}
where position_index > 4
