-- one row per measurement, keyed by its business key
-- - silver is already at this grain: the joins only add pp_number
-- - precision reduced: date_time to the second, the decimals to 2
with
    -- the room. a left join: staging checked the position once, at load time, and a seed change can remove it later
    assign_room as (
        select journal_entries.*, absolute_positions.room
        from {{ ref("slvr_journal_entries") }} as journal_entries
        left join
            {{ ref("dim_absolute_positions") }} as absolute_positions
            on journal_entries.absolute_position = absolute_positions.absolute_position
    ),

    -- the local day of the measurement
    assign_local_date as (
        select *, (date_time at time zone '{{ var("timezone") }}')::date as local_date from assign_room
    ),

    -- the batch flowering in the room on the local day, both dates included. null when there is none
    -- TODO staging refuses only identical flowering dates: an overlap repeats the row and fails the primary key
    assign_plants_batch as (
        select assign_local_date.*, plants_batches.pp_number
        from assign_local_date
        left join
            {{ ref("dim_plants_batches") }} as plants_batches
            on assign_local_date.room = plants_batches.room
            and assign_local_date.local_date between plants_batches.date_flower_start and plants_batches.date_flower_end
    )



select
    row_id,
    -- truncated, not rounded, so 23:59:59.7 stays on its day
    date_trunc('second', date_time)::timestamptz(0) as date_time,
    device,
    absolute_position,
    pp_number,
    ml,
    -- the cast rounds half away from zero (5.125 to 5.13)
    ec::numeric(4, 2) as ec,
    ph::numeric(4, 2) as ph,
    temperature::numeric(4, 2) as temperature,
    remarks,
    reading_status
from assign_plants_batch
