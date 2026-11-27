-- the journal entries, typed. the csv is written by a program of ours, so only this is mapped:
-- - empty to null
-- - remarks trimmed
-- - the time zone appended
-- - spot to relative position
-- anything else is an upstream fault and fails a data test
with
    -- the open load only (landed or accepted): there is at most one, so every data test judges it alone
    select_open_load as (
        select *
        from {{ source("dw_bronze", "brnz_journal_entries") }}
        where load_id in ({{ loads_in_state(["landed", "accepted"]) }})
    ),

    -- empty means null
    -- - n.a becomes null in cast_select, as it cannot be cast. reading_status says where a null is allowed
    nullify_empty as (
        select
            row_id,
            -- measured, unreliable or skipped, decided by the web app and taken as sent: it says which nulls the
            -- data tests allow, see stg_journal_entries.yml
            nullif(reading_status, '') as reading_status,
            nullif(date_time, '') as date_time,
            nullif(device, '') as device,
            nullif(spot, '') as spot,
            nullif(ml, '') as ml,
            nullif(ec, '') as ec,
            nullif(ph, '') as ph,
            nullif(temperature, '') as temperature,
            nullif(room, '') as room,
            nullif(bench, '') as bench,
            -- free text: trimmed, null only when blank
            nullif(trim(remarks), '') as remarks
        from select_open_load
    ),

    -- the csv sends no zone, so the timezone var is appended: a name, not an offset, so each date gets its own
    -- daylight saving
    -- - n.a stays n.a plus the zone, and becomes null in cast_select
    -- TODO take the zone from the csv
    append_timezone as (
        select
            row_id,
            reading_status,
            date_time || ' {{ var("timezone") }}' as date_time,
            device,
            spot,
            ml,
            ec,
            ph,
            temperature,
            room,
            bench,
            remarks
        from nullify_empty
    ),

    -- spot to relative position, such as drip_left to front_left_up:
    -- - always front
    -- - drip is up, drain is down
    -- - any other value is null and fails not_null
    map_relative_position as (
        select
            row_id,
            reading_status,
            date_time,
            device,
            case
                when spot ~ '^(drip|drain)_(left|right)$'
                then
                    'front_'
                    || split_part(spot, '_', 2)
                    || case when split_part(spot, '_', 1) = 'drip' then '_up' else '_down' end
            end as relative_position,
            ml,
            ec,
            ph,
            temperature,
            room,
            bench,
            remarks
        from append_timezone
    ),

    -- the place, such as 1.30_4_front_left_up:
    -- - null when a part is null, so not_null fails
    -- - a combination that does not exist fails the relationships test, such as a bench the room has not
    -- - room, bench and relative_position are dropped by cast_select, which keeps only the yml's columns
    assign_absolute_position as (
        select
            row_id,
            reading_status,
            date_time,
            device,
            room || '_' || bench || '_' || relative_position as absolute_position,
            ml,
            ec,
            ph,
            temperature,
            remarks
        from map_relative_position
    )

    {{ cast_select("assign_absolute_position") }}
