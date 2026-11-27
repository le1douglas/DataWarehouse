-- one row per measurement, keyed by its business key
-- - silver is already at this grain: the joins only add pp_number
-- - precision reduced: date_time to the second, the decimals to 2
with
-- the room. a left join: staging checked the position once, at load time, and a seed change can remove it later
journal_entries as (select * from {{ ref("slvr_journal_entries") }}),

absolute_positions as (select * from {{ ref("dim_absolute_positions") }}),

plants_batches as (select * from {{ ref("dim_plants_batches") }}),

assign_room as (
    select
        journal_entries.row_id,
        absolute_positions.room
    from journal_entries
    left join absolute_positions on journal_entries.absolute_position = absolute_positions.absolute_position
),

assign_dates as (
    select
        journal_entries.row_id,
        -- original date_time, truncated so 23:59:59.7 stays on its day
        date_trunc('second', journal_entries.date_time)::timestamptz (0) as date_time,
        -- the local date
        (journal_entries.date_time at time zone '{{ var("timezone") }}')::date as local_date
    from journal_entries
),

-- the batch flowering in the room on the local day, both dates included. null when there is none
-- TODO staging refuses only identical flowering dates: an overlap repeats the row and fails the primary key
assign_plants_batch as (
    select
        assign_room.row_id,
        plants_batches.pp_number
    from assign_room
    left join assign_dates on assign_room.row_id = assign_dates.row_id
    left join plants_batches on
        assign_room.room = plants_batches.room
        and assign_dates.local_date between plants_batches.date_flower_start and plants_batches.date_flower_end
),

assign_values as (
    select
        journal_entries.row_id,
        journal_entries.ec::numeric(4, 2) as ec,
        journal_entries.ph::numeric(4, 2) as ph,
        journal_entries.temperature::numeric(4, 2) as temperature
    from journal_entries
)


select
    journal_entries.row_id,
    assign_dates.date_time,
    journal_entries.device,
    journal_entries.absolute_position,
    assign_plants_batch.pp_number,
    journal_entries.ml,
    assign_values.ec,
    assign_values.ph,
    assign_values.temperature,
    journal_entries.remarks,
    journal_entries.reading_status

from journal_entries
left join assign_dates on journal_entries.row_id = assign_dates.row_id
left join assign_plants_batch on journal_entries.row_id = assign_plants_batch.row_id
left join assign_values on journal_entries.row_id = assign_values.row_id
