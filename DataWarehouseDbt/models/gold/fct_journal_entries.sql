-- one row per measurement, keyed by its business key
-- - silver is already at this grain: the joins only add pp_number
-- - precision reduced: date_time to the second, the decimals to 2
select
    journal_entries.row_id,
    -- truncated, not rounded, so 23:59:59.7 stays on its day. the cast only declares the precision
    date_trunc('second', journal_entries.date_time)::timestamptz(0) as date_time,
    journal_entries.device,
    journal_entries.absolute_position,
    -- null when no batch is flowering in the room that day
    plants_batches.pp_number,
    journal_entries.ml,
    -- the cast rounds half away from zero (5.125 to 5.13). staging's ranges fit numeric(4,2)
    journal_entries.ec::numeric(4, 2) as ec,
    journal_entries.ph::numeric(4, 2) as ph,
    journal_entries.temperature::numeric(4, 2) as temperature,
    journal_entries.remarks,
    -- measured, unreliable or skipped: the measures of the last two may be null
    journal_entries.reading_status
from {{ ref("slvr_journal_entries") }} as journal_entries
-- the room. a left join: staging checked the position once, at load time, and a seed change can remove it later
left join
    {{ ref("dim_absolute_positions") }} as absolute_positions
    on journal_entries.absolute_position = absolute_positions.absolute_position
-- the batch flowering in the room on the local day of the measurement, both dates included
-- - staging refuses only identical flowering dates: an overlap repeats the row and fails the primary key
left join
    {{ ref("dim_plants_batches") }} as plants_batches
    on absolute_positions.room = plants_batches.room
    and (journal_entries.date_time at time zone '{{ var("timezone") }}')::date
    between plants_batches.date_flower_start and plants_batches.date_flower_end
