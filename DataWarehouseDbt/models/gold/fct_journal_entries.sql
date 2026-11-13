-- the journal entries as a fact: one row per measurement, keyed by row_id, with a key to each dimension and the
-- measures. silver is already at this grain: the joins only add pp_number, the batch flowering in the room of the
-- measurement on its day. silver keeps the precision the csv sends, gold reduces it: date_time to the second, the
-- decimals to 2
select
    journal_entries.row_id,
    -- truncated, not rounded: 23:59:59.7 stays on its day. the cast only declares the precision
    date_trunc('second', journal_entries.date_time)::timestamptz(0) as date_time,
    journal_entries.device,
    journal_entries.absolute_position,
    -- null when no batch is flowering in that room on that day
    plants_batches.pp_number,
    journal_entries.ml,
    -- the cast rounds half away from zero: 5.125 becomes 5.13. silver's ranges fit in numeric(4,2)
    journal_entries.ec::numeric(4, 2) as ec,
    journal_entries.ph::numeric(4, 2) as ph,
    journal_entries.temperature::numeric(4, 2) as temperature
from {{ ref("slvr_journal_entries") }} as journal_entries
-- the room of the measurement. the foreign key on absolute_position guarantees a match
left join
    {{ ref("dim_absolute_positions") }} as absolute_positions
    on journal_entries.absolute_position = absolute_positions.absolute_position
-- a batch is in its room from date_flower_start to date_flower_end, both days included, compared with the local day
-- of the measurement. one batch per room at a time, so a measurement matches at most one: an overlap would repeat it
left join
    {{ ref("dim_plants_batches") }} as plants_batches
    on absolute_positions.room = plants_batches.room
    and (journal_entries.date_time at time zone '{{ var("timezone") }}')::date
    between plants_batches.date_flower_start and plants_batches.date_flower_end
