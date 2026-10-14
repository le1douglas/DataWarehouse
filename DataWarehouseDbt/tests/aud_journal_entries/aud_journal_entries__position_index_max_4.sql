select * from {{ ref("cand_journal_entries") }} where position_index > 4
