-- the journal entries as the growers' daily sheet: one row per room per day. each room is measured at four positions,
-- up is the drip of one plant, down the drain of 3 plants, on the left and the right side. bench and depth are always
-- the same, so they are left out. one reading per position per day is assumed, to be guarded upstream
-- (docs/REMINDERS.md): any_value() takes that one
with
    readings as (
        select
            absolute_positions.room,
            -- the local day of the measurement, as fct_journal_entries uses it to find the batch
            (journal_entries.date_time at time zone '{{ var("timezone") }}')::date as date,
            journal_entries.pp_number,
            absolute_positions.horizontal,
            absolute_positions.vertical,
            journal_entries.ml,
            journal_entries.ec,
            journal_entries.ph
        from {{ ref("fct_journal_entries") }} as journal_entries
        inner join
            {{ ref("dim_absolute_positions") }} as absolute_positions
            on journal_entries.absolute_position = absolute_positions.absolute_position
    ),

    pivoted as (
        -- pp_number depends only on the room and the day, so grouping by it adds no rows
        select
            room,
            date,
            pp_number,
            any_value(ph) filter (where horizontal = 'left' and vertical = 'up') as left_drip_ph,
            any_value(ec) filter (where horizontal = 'left' and vertical = 'up') as left_drip_ec,
            any_value(ml) filter (where horizontal = 'left' and vertical = 'up') as left_drip_ml,
            any_value(ph) filter (where horizontal = 'left' and vertical = 'down') as left_drain_ph,
            any_value(ec) filter (where horizontal = 'left' and vertical = 'down') as left_drain_ec,
            any_value(ml) filter (where horizontal = 'left' and vertical = 'down') as left_drain_ml,
            any_value(ph) filter (where horizontal = 'right' and vertical = 'up') as right_drip_ph,
            any_value(ec) filter (where horizontal = 'right' and vertical = 'up') as right_drip_ec,
            any_value(ml) filter (where horizontal = 'right' and vertical = 'up') as right_drip_ml,
            any_value(ph) filter (where horizontal = 'right' and vertical = 'down') as right_drain_ph,
            any_value(ec) filter (where horizontal = 'right' and vertical = 'down') as right_drain_ec,
            any_value(ml) filter (where horizontal = 'right' and vertical = 'down') as right_drain_ml
        from readings
        group by room, date, pp_number
    )

-- the drain is of 3 plants, always: per plant it is divided by 3.0, not 3, which would be an integer division. the
-- percentage divides the unrounded value, so it is rounded once. null when the drip is missing or 0
-- the grosens columns are WIP until their data arrives: then they become columns of a dataset of their own
-- the remarks are null until the source sends them (docs/REMINDERS.md)
select
    room,
    pp_number,
    date,
    'WIP'::text as left_grosens_ec_low,
    'WIP'::text as left_grosens_ec_high,
    'WIP'::text as left_grosens_wc_low,
    'WIP'::text as left_grosens_wc_high,
    left_drip_ph,
    left_drip_ec,
    left_drip_ml,
    null::text as left_drip_remarks,
    left_drain_ph,
    left_drain_ec,
    left_drain_ml,
    null::text as left_drain_remarks,
    round(left_drain_ml / 3.0)::integer as left_drain_ml_per_plant,
    round(left_drain_ml / 3.0 / nullif(left_drip_ml, 0) * 100, 1)::numeric(5, 1) as left_drain_percentage,
    'WIP'::text as right_grosens_ec_low,
    'WIP'::text as right_grosens_ec_high,
    'WIP'::text as right_grosens_wc_low,
    'WIP'::text as right_grosens_wc_high,
    right_drip_ph,
    right_drip_ec,
    right_drip_ml,
    null::text as right_drip_remarks,
    right_drain_ph,
    right_drain_ec,
    right_drain_ml,
    null::text as right_drain_remarks,
    round(right_drain_ml / 3.0)::integer as right_drain_ml_per_plant,
    round(right_drain_ml / 3.0 / nullif(right_drip_ml, 0) * 100, 1)::numeric(5, 1) as right_drain_percentage
from pivoted
