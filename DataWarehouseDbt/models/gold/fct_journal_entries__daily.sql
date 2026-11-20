-- the growers' daily sheet: one row per flowering room per day, from the first measured day to today
-- - a day without readings is a row too, so a missing reading shows
-- - four positions per room: left and right, up is the drip of one plant, down the drain of 3
-- - bench and depth never change, so they are left out
-- - staging refuses a second reading of a position on one local day, so any_value() takes the only one
with


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

find_date_ranges as (
    select
        (min(date_time) at time zone '{{ var("timezone") }}')::date as first_date,
        -- either today or the last date with a reading, whichever is later
        greatest(
            (max(date_time) at time zone '{{ var("timezone") }}')::date,
            (now() at time zone '{{ var("timezone") }}')::date
        ) as last_date
    from journal_entries
),

spine_date_room as (
    select
        dim_rooms.room,
        dim_rooms.room_time,
        generate_series(find_date_ranges.first_date, find_date_ranges.last_date, interval '1 day')::date as local_date
    from dim_rooms
    cross join find_date_ranges
),


-- PREPARE journal_entries

-- each measure, and its default value to siplay when null
{% set measures = {
    "ph": "null",
    "ec": "null",
    "ml": "null",
    "remarks": "null",
    "reading_status": "'missing'"
} %}
{% set horizontals = ["left", "right"] %}
{% set verticals = ["drip", "drain"] %}

-- maps up and down to drip and drain
assign_position as (
    select
        journal_entries.*,
        dim_absolute_positions.room,
        dim_absolute_positions.horizontal,
        case dim_absolute_positions.vertical
            when 'up' then 'drip'
            when 'down' then 'drain'
        end as vertical
    from journal_entries
    left join dim_absolute_positions using (absolute_position)
),

-- joins all the dimentions we want to display to the readings
join_dimensions as (
    select
        assign_position.room,
        (assign_position.date_time at time zone '{{ var("timezone") }}')::date as local_date,
        assign_position.horizontal,
        assign_position.vertical,
        assign_position.pp_number,
        dim_plants_batches.strain,
    {% for measure in measures %}
        assign_position.{{ measure }}{{ "," if not loop.last }}
    {% endfor %}
    from assign_position
    left join dim_plants_batches using (pp_number)
),


-- PIVOT 


pivot_readings as (
    select
        spine_date_room.room,
        spine_date_room.room_time,
        spine_date_room.local_date,
    {% for horizontal in horizontals %}
    {% for vertical in verticals %}
        {% for measure, default_value in measures.items() %}
            coalesce(

                any_value(join_dimensions.{{ measure }}) filter (
                    where join_dimensions.horizontal = '{{ horizontal }}'
                    and join_dimensions.vertical = '{{ vertical }}'
                ),

                {{ default_value }}
            ) as {{ horizontal }}_{{ vertical }}_{{ measure }}{{ "," if not loop.last }}
        {% endfor %}{{ "," if not loop.last }}
        {% endfor %}{{ "," if not loop.last }}
    {% endfor %}
    from spine_date_room
    left join join_dimensions using (room, local_date)
    group by spine_date_room.room, spine_date_room.room_time, spine_date_room.local_date
),


-- one row per room per day with readings: the same for every position, so any_value() takes it
collapse_dimensions as (
    select
        join_dimensions.room,
        join_dimensions.local_date,
        any_value(join_dimensions.pp_number) as pp_number,
        any_value(join_dimensions.strain) as strain
    from join_dimensions
    group by join_dimensions.room, join_dimensions.local_date
),

-- a day without readings has no dimensions
join_pivot_and_dimensions as (
    select *
    from pivot_readings
    left join collapse_dimensions using (room, local_date)
),


-- ADD DERIVED AND PLACEHOLDER COLUMNS


generate_placeholders as (
    select
        join_pivot_and_dimensions.*,
    {% for horizontal in horizontals %}
        null::text as {{ horizontal }}_grosens_ec_low,
        null::text as {{ horizontal }}_grosens_ec_high,
        null::text as {{ horizontal }}_grosens_wc_low,
        null::text as {{ horizontal }}_grosens_wc_high{{ "," if not loop.last }}
    {% endfor %}
    from join_pivot_and_dimensions
),


generate_iso_dates as (
    select
        generate_placeholders.*,
        extract(isoyear from generate_placeholders.local_date)::int as iso_year,
        extract(week from generate_placeholders.local_date)::int as iso_week
    from generate_placeholders
),


generate_drain_ml_per_plant as (
    select
        generate_iso_dates.*,
    {% for horizontal in horizontals %}
        round({{ horizontal }}_drain_ml / 3.0)::integer
            as {{ horizontal }}_drain_ml_per_plant{{ "," if not loop.last }}
    {% endfor %}
    from generate_iso_dates
),


generate_drain_percentage as (
    select
        generate_drain_ml_per_plant.*,
    {% for horizontal in horizontals %}
        round({{ horizontal }}_drain_ml_per_plant::numeric / nullif({{ horizontal }}_drip_ml, 0), 3)::numeric(5, 3)
            as {{ horizontal }}_drain_percentage{{ "," if not loop.last }}
    {% endfor %}
    from generate_drain_ml_per_plant
),


-- the grosens columns are placeholders until their data arrives, as a dataset of its own
final as (
    select
        room,
        room_time,
        strain,
        pp_number,
        local_date,
        iso_year,
        iso_week,
        left_grosens_ec_low,
        left_grosens_ec_high,
        left_grosens_wc_low,
        left_grosens_wc_high,
        left_drip_ph,
        left_drip_ec,
        left_drip_ml,
        left_drip_remarks,
        left_drip_reading_status,
        left_drain_ph,
        left_drain_ec,
        left_drain_ml,
        left_drain_remarks,
        left_drain_reading_status,
        left_drain_ml_per_plant,
        left_drain_percentage,
        right_grosens_ec_low,
        right_grosens_ec_high,
        right_grosens_wc_low,
        right_grosens_wc_high,
        right_drip_ph,
        right_drip_ec,
        right_drip_ml,
        right_drip_remarks,
        right_drip_reading_status,
        right_drain_ph,
        right_drain_ec,
        right_drain_ml,
        right_drain_remarks,
        right_drain_reading_status,
        right_drain_ml_per_plant,
        right_drain_percentage
    from generate_drain_percentage
)


select * from final
