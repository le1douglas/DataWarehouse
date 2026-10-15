select row_id, 'position_index ' || position_index as description
from {{ ref("cand_journal_entries") }}
where position_index > 4
