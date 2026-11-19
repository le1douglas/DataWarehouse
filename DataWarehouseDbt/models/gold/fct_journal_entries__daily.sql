-- the growers' daily sheet: one row per flowering room per day, from the first measured day to today
-- - a day without readings is a row too, so a missing reading shows
-- - four positions per room: left and right, up is the drip of one plant, down the drain of 3
-- - bench and depth never change, so they are left out
-- - staging refuses a second reading of a position on one local day, so any_value() takes the only one
with
    readings as (
        select
            absolute_positions.room,
            -- the local day, as fct_journal_entries uses it to find the batch
            (journal_entries.date_time at time zone '{{ var("timezone") }}')::date as date,
            absolute_positions.horizontal,
            absolute_positions.vertical,
            journal_entries.ml,
            journal_entries.ec,
            journal_entries.ph,
            journal_entries.remarks
        from {{ ref("fct_journal_entries") }} as journal_entries
        inner join
            {{ ref("dim_absolute_positions") }} as absolute_positions
            on journal_entries.absolute_position = absolute_positions.absolute_position
    ),

    pivoted as (
        select
            room,
            date,
            any_value(ph) filter (where horizontal = 'left' and vertical = 'up') as left_drip_ph,
            any_value(ec) filter (where horizontal = 'left' and vertical = 'up') as left_drip_ec,
            any_value(ml) filter (where horizontal = 'left' and vertical = 'up') as left_drip_ml,
            any_value(remarks) filter (where horizontal = 'left' and vertical = 'up') as left_drip_remarks,
            any_value(ph) filter (where horizontal = 'left' and vertical = 'down') as left_drain_ph,
            any_value(ec) filter (where horizontal = 'left' and vertical = 'down') as left_drain_ec,
            any_value(ml) filter (where horizontal = 'left' and vertical = 'down') as left_drain_ml,
            any_value(remarks) filter (where horizontal = 'left' and vertical = 'down') as left_drain_remarks,
            any_value(ph) filter (where horizontal = 'right' and vertical = 'up') as right_drip_ph,
            any_value(ec) filter (where horizontal = 'right' and vertical = 'up') as right_drip_ec,
            any_value(ml) filter (where horizontal = 'right' and vertical = 'up') as right_drip_ml,
            any_value(remarks) filter (where horizontal = 'right' and vertical = 'up') as right_drip_remarks,
            any_value(ph) filter (where horizontal = 'right' and vertical = 'down') as right_drain_ph,
            any_value(ec) filter (where horizontal = 'right' and vertical = 'down') as right_drain_ec,
            any_value(ml) filter (where horizontal = 'right' and vertical = 'down') as right_drain_ml,
            any_value(remarks) filter (where horizontal = 'right' and vertical = 'down') as right_drain_remarks
        from readings
        group by room, date
    ),

    -- every flowering room on every day from the first measured day to today
    -- - a day no room was measured shows too, empty for every room
    -- - today is the local day of the build, or the last measured day when a reading is dated later
    room_days as (
        select rooms.room, rooms.room_time, days.date::date as date
        from {{ ref("dim_rooms") }} as rooms
        cross join
            generate_series(
                (select min(date) from readings),
                greatest((select max(date) from readings), (now() at time zone '{{ var("timezone") }}')::date),
                interval '1 day'
            ) as days(date)
        where rooms.assigned_stage = 'flowering'
    )

-- each room's day with its readings, null when it has none:
-- - strain and pp_number: the batch flowering that day, found as in fct_journal_entries, so a day without
--   readings has them too. an overlap repeats the row and fails the primary key
-- - drain per plant divides by 3.0: 3 would be an integer division
-- - the percentage divides the unrounded value and is rounded once, to 0.1 %. a fraction (0.174 for 17.4 %),
--   as Excel and Power BI percent formats expect. null when the drip is missing or 0
-- - the grosens columns are placeholders until their data arrives, as a dataset of its own
-- - iso_week and iso_year: monday to sunday, in the year of the week's thursday
select
    room_days.room,
    room_days.room_time,
    plants_batches.strain,
    plants_batches.pp_number,
    room_days.date,
    extract(isoyear from room_days.date)::integer as iso_year,
    extract(week from room_days.date)::integer as iso_week,
    null::text as left_grosens_ec_low,
    null::text as left_grosens_ec_high,
    null::text as left_grosens_wc_low,
    null::text as left_grosens_wc_high,
    left_drip_ph,
    left_drip_ec,
    left_drip_ml,
    left_drip_remarks,
    left_drain_ph,
    left_drain_ec,
    left_drain_ml,
    left_drain_remarks,
    round(left_drain_ml / 3.0)::integer as left_drain_ml_per_plant,
    round(left_drain_ml / 3.0 / nullif(left_drip_ml, 0), 3)::numeric(5, 3) as left_drain_percentage,
    null::text as right_grosens_ec_low,
    null::text as right_grosens_ec_high,
    null::text as right_grosens_wc_low,
    null::text as right_grosens_wc_high,
    right_drip_ph,
    right_drip_ec,
    right_drip_ml,
    right_drip_remarks,
    right_drain_ph,
    right_drain_ec,
    right_drain_ml,
    right_drain_remarks,
    round(right_drain_ml / 3.0)::integer as right_drain_ml_per_plant,
    round(right_drain_ml / 3.0 / nullif(right_drip_ml, 0), 3)::numeric(5, 3) as right_drain_percentage
from room_days
left join pivoted on room_days.room = pivoted.room and room_days.date = pivoted.date
left join
    {{ ref("dim_plants_batches") }} as plants_batches
    on room_days.room = plants_batches.room
    and room_days.date between plants_batches.date_flower_start and plants_batches.date_flower_end
