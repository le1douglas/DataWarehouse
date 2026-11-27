-- the growers' daily sheet: one row per flowering room per day, from the first measured day to today
-- - a day without readings is a row too, so a missing reading shows
-- - four positions per room: left and right, up is the drip of one plant, down the drain of 3
-- - bench and depth never change, so they are left out
-- - staging refuses a second reading of a position on one local day, so any_value() takes the only one
-- - each cte returns room, local_date and only its own columns; final joins them onto the spine
with


-- IMPORTS


journal_entries as (
    select * from {{ ref("fct_journal_entries") }}
),


dim_absolute_positions as (
    select * from {{ ref("dim_absolute_positions") }}
),

dim_plants_batches as (
    select * from {{ ref("dim_plants_batches") }}
),

dim_rooms as (
    select * from {{ ref("dim_rooms") }}
    where
        assigned_stage = 'flowering'
),






-- SPINE

find_date_ranges as (
    select
        (min(journal_entries.date_time) at time zone '{{ var("timezone") }}')::date as first_date,
        -- either today or the last date with a reading, whichever is later
        greatest(
            (max(journal_entries.date_time) at time zone '{{ var("timezone") }}')::date,
            (now() at time zone '{{ var("timezone") }}')::date
        ) as last_date
    from journal_entries
),

spine_date_room as (
    select
        dim_rooms.room,
        generate_series(find_date_ranges.first_date, find_date_ranges.last_date, interval '1 day')::date as local_date
    from dim_rooms
    cross join find_date_ranges
),






-- PREPARE journal_entries


-- maps up and down to drip and drain, more business useful terms
assign_position as (
    select
        journal_entries.row_id,
        dim_absolute_positions.room,
        (journal_entries.date_time at time zone '{{ var("timezone") }}')::date as local_date,
        dim_absolute_positions.horizontal,
        case dim_absolute_positions.vertical
            when 'up' then 'drip'
            when 'down' then 'drain'
        end as vertical
    from journal_entries
    left join dim_absolute_positions using (absolute_position)
),







-- PIVOT


-- each measure of the pivot, and its default value to display when null
{% set measures = {
    "ph": "null",
    "ec": "null",
    "ml": "null",
    "remarks": "null",
    "reading_status": "'missing'"
} %}
{% set horizontals = ["left", "right"] %}
{% set verticals = ["drip", "drain"] %}

-- from the spine, so a day without readings gets the default values too
pivot_readings as (
    select
        spine_date_room.room,
        spine_date_room.local_date,
    {% for horizontal in horizontals %}
    {% for vertical in verticals %}
        {% for measure, default_value in measures.items() %}
            coalesce(

                any_value(journal_entries.{{ measure }}) filter (
                    where assign_position.horizontal = '{{ horizontal }}'
                    and assign_position.vertical = '{{ vertical }}'
                ),

                {{ default_value }}
            ) as {{ horizontal }}_{{ vertical }}_{{ measure }}{{ "," if not loop.last }}
        {% endfor %}{{ "," if not loop.last }}
        {% endfor %}{{ "," if not loop.last }}
    {% endfor %}
    from spine_date_room
    left join assign_position using (room, local_date)
    left join journal_entries using (row_id)
    group by spine_date_room.room, spine_date_room.local_date
),


-- ADD DIMENSIONS

-- the batch flowering in each room on each day, from its dates, so a day without readings has it too
-- - batches in one room never overlap, so a day has at most one
assign_plants_batch as (
    select
        spine_date_room.room,
        spine_date_room.local_date,
        dim_plants_batches.pp_number,
        dim_plants_batches.strain
    from spine_date_room
    left join dim_plants_batches
        on
            spine_date_room.room = dim_plants_batches.room
            and spine_date_room.local_date
            between dim_plants_batches.date_flower_start and dim_plants_batches.date_flower_end
),





-- ADD DERIVED AND PLACEHOLDER COLUMNS

-- the grosens columns are placeholders until their data arrives, as a dataset of its own
generate_placeholders as (
    select
        spine_date_room.room,
        spine_date_room.local_date,
    {% for horizontal in horizontals %}
        null::text as {{ horizontal }}_grosens_ec_low,
        null::text as {{ horizontal }}_grosens_ec_high,
        null::text as {{ horizontal }}_grosens_wc_low,
        null::text as {{ horizontal }}_grosens_wc_high{{ "," if not loop.last }}
    {% endfor %}
    from spine_date_room
),


-- useful for filtering
generate_iso_dates as (
    select
        spine_date_room.room,
        spine_date_room.local_date,
        extract(isoyear from spine_date_room.local_date)::int as iso_year,
        extract(week from spine_date_room.local_date)::int as iso_week
    from spine_date_room
),



-- the normal drain_ml is the measurement of 3 plants. Get the value for 1
generate_drain_ml_per_plant as (
    select
        pivot_readings.room,
        pivot_readings.local_date,
    {% for horizontal in horizontals %}
        round(pivot_readings.{{ horizontal }}_drain_ml / 3.0)::integer
            as {{ horizontal }}_drain_ml_per_plant{{ "," if not loop.last }}
    {% endfor %}
    from pivot_readings
),



-- ratio between a single plant drip_ml and a single plant drain_ml
generate_drain_percentage as (
    select
        pivot_readings.room,
        pivot_readings.local_date,
    {% for horizontal in horizontals %}
        round(
            generate_drain_ml_per_plant.{{ horizontal }}_drain_ml_per_plant::numeric
            / nullif(pivot_readings.{{ horizontal }}_drip_ml, 0),
            3
        )::numeric(5, 3)
        as {{ horizontal }}_drain_percentage{{ "," if not loop.last }}
    {% endfor %}
    from pivot_readings
    left join generate_drain_ml_per_plant using (room, local_date)
),


final as (
    select
        spine_date_room.room,
        dim_rooms.room_time,
        assign_plants_batch.strain,
        assign_plants_batch.pp_number,
        spine_date_room.local_date,
        generate_iso_dates.iso_year,
        generate_iso_dates.iso_week,
        generate_placeholders.left_grosens_ec_low,
        generate_placeholders.left_grosens_ec_high,
        generate_placeholders.left_grosens_wc_low,
        generate_placeholders.left_grosens_wc_high,
        pivot_readings.left_drip_ph,
        pivot_readings.left_drip_ec,
        pivot_readings.left_drip_ml,
        pivot_readings.left_drip_remarks,
        pivot_readings.left_drip_reading_status,
        pivot_readings.left_drain_ph,
        pivot_readings.left_drain_ec,
        pivot_readings.left_drain_ml,
        pivot_readings.left_drain_remarks,
        pivot_readings.left_drain_reading_status,
        generate_drain_ml_per_plant.left_drain_ml_per_plant,
        generate_drain_percentage.left_drain_percentage,
        generate_placeholders.right_grosens_ec_low,
        generate_placeholders.right_grosens_ec_high,
        generate_placeholders.right_grosens_wc_low,
        generate_placeholders.right_grosens_wc_high,
        pivot_readings.right_drip_ph,
        pivot_readings.right_drip_ec,
        pivot_readings.right_drip_ml,
        pivot_readings.right_drip_remarks,
        pivot_readings.right_drip_reading_status,
        pivot_readings.right_drain_ph,
        pivot_readings.right_drain_ec,
        pivot_readings.right_drain_ml,
        pivot_readings.right_drain_remarks,
        pivot_readings.right_drain_reading_status,
        generate_drain_ml_per_plant.right_drain_ml_per_plant,
        generate_drain_percentage.right_drain_percentage
    from spine_date_room
    left join dim_rooms using (room)
    left join assign_plants_batch using (room, local_date)
    left join pivot_readings using (room, local_date)
    left join generate_placeholders using (room, local_date)
    left join generate_iso_dates using (room, local_date)
    left join generate_drain_ml_per_plant using (room, local_date)
    left join generate_drain_percentage using (room, local_date)
)


select * from final
