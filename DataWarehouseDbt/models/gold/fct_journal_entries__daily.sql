-- the growers' daily sheet: one row per flowering room per day, from the first measured day to today
-- - a day without readings is a row too, so a missing reading shows
-- - four positions per room: left and right, up is the drip of one plant, down the drain of 3
-- - bench and depth never change, so they are left out
-- - staging refuses a second reading of a position on one local day, so any_value() takes the only one
with
    -- the readings, at the precision gold presents them
    select_readings as (
        select date_time, absolute_position, ml, ec, ph, remarks, reading_status from {{ ref("fct_journal_entries") }}
    ),

    -- the local day, as fct_journal_entries uses it to find the batch
    assign_local_date as (
        select *, (date_time at time zone '{{ var("timezone") }}')::date as date from select_readings
    ),

    -- the room and the place on the bench of each reading
    locate_readings as (
        select assign_local_date.*, absolute_positions.room, absolute_positions.horizontal, absolute_positions.vertical
        from assign_local_date
        inner join
            {{ ref("dim_absolute_positions") }} as absolute_positions
            on assign_local_date.absolute_position = absolute_positions.absolute_position
    ),

    -- from the first measured day to today
    -- - today is the local day of the build, or the last measured day when a reading is dated later
    find_date_range as (
        select
            min(date) as first_date,
            greatest(max(date), (now() at time zone '{{ var("timezone") }}')::date) as last_date
        from locate_readings
    ),

    -- every cell of the sheet: each flowering room, at each of its positions, on each day of the range
    -- - a day no room was measured shows too, empty for every room
    generate_sheet_cells as (
        select 
        positions.room, 
        rooms.room_time, 
        positions.horizontal, 
        positions.vertical, 
        days.date::date as date
        from (select distinct room, horizontal, vertical from {{ ref("dim_absolute_positions") }}) as positions
        inner join {{ ref("dim_rooms") }} as rooms on positions.room = rooms.room
        cross join find_date_range
        cross join
            generate_series(find_date_range.first_date, find_date_range.last_date, interval '1 day') as days(date)
        where rooms.assigned_stage = 'flowering'
    ),

    -- each cell with its reading, missing when it has none
    -- - using keeps one room, date, horizontal and vertical, those of the cell
    fill_missing_readings as (
        select
            room,
            room_time,
            date,
            horizontal,
            vertical,
            ml,
            ec,
            ph,
            remarks,
            coalesce(reading_status, 'missing') as reading_status
        from generate_sheet_cells
        left join locate_readings using (room, date, horizontal, vertical)
    ),

    -- one row per room per day, one column per position and measure, such as left_drip_ph
    -- - a position is named left or right, then drip (up) or drain (down)
    pivot_positions as (
        select
            {% for horizontal in ["left", "right"] %}
                {% for vertical, side in [("up", "drip"), ("down", "drain")] %}
                    {% for measure in ["ph", "ec", "ml", "remarks", "reading_status"] %}
                        any_value({{ measure }}) filter (
                            where horizontal = '{{ horizontal }}' and vertical = '{{ vertical }}'
                        ) as {{ horizontal }}_{{ side }}_{{ measure }},
                    {% endfor %}
                {% endfor %}
            {% endfor %}
            room,
            room_time,
            date
        from fill_missing_readings
        group by room, room_time, date
    ),

    -- the batch flowering that day, found as in fct_journal_entries, so a day without readings has it too
    -- - an overlap repeats the row and fails the primary key
    assign_plants_batch as (
        select pivot_positions.*, plants_batches.strain, plants_batches.pp_number
        from pivot_positions
        left join
            {{ ref("dim_plants_batches") }} as plants_batches
            on pivot_positions.room = plants_batches.room
            and pivot_positions.date between plants_batches.date_flower_start and plants_batches.date_flower_end
    ),

    -- the drain per plant and as a share of the drip
    -- - divides by 3.0: 3 would be an integer division
    -- - the percentage divides the unrounded value and is rounded once, to 0.1 %. a fraction (0.174 for 17.4 %),
    -- as Excel and Power BI percent formats expect. null when the drip is missing or 0
    compute_drain as (
        select
            *,
            round(left_drain_ml / 3.0)::integer as left_drain_ml_per_plant,
            round(left_drain_ml / 3.0 / nullif(left_drip_ml, 0), 3)::numeric(5, 3) as left_drain_percentage,
            round(right_drain_ml / 3.0)::integer as right_drain_ml_per_plant,
            round(right_drain_ml / 3.0 / nullif(right_drip_ml, 0), 3)::numeric(5, 3) as right_drain_percentage
        from assign_plants_batch
    ),

    -- monday to sunday, in the year of the week's thursday
    assign_iso_week as (
        select *, extract(isoyear from date)::integer as iso_year, extract(week from date)::integer as iso_week
        from compute_drain
    )

-- the grosens columns are placeholders until their data arrives, as a dataset of its own
select
    room,
    room_time,
    strain,
    pp_number,
    date,
    iso_year,
    iso_week,
    null::text as left_grosens_ec_low,
    null::text as left_grosens_ec_high,
    null::text as left_grosens_wc_low,
    null::text as left_grosens_wc_high,
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
    null::text as right_grosens_ec_low,
    null::text as right_grosens_ec_high,
    null::text as right_grosens_wc_low,
    null::text as right_grosens_wc_high,
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
from assign_iso_week
