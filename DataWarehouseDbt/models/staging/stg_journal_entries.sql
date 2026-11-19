-- the journal entries, typed. the csv is written by a program of ours, so only this is mapped:
-- - empty to null
-- - the time zone appended
-- - spot to relative position, and the bench added
-- - remarks trimmed
-- anything else is an upstream fault and fails a data test
with
    mapped as (
        select
            row_id,
            -- the csv sends no zone, so the timezone var is appended: a name, not an offset, so each date gets its own
            -- daylight saving
            -- TODO take the zone from the csv
            nullif(date_time, '') || ' {{ var("timezone") }}' as date_time,
            nullif(device, '') as device,
            -- spot to relative position, such as drip_left to front_left_up:
            -- - always front
            -- - drip is up, drain is down
            -- - any other value is null and fails not_null
            case
                when spot ~ '^(drip|drain)_(left|right)$'
                then
                    'front_'
                    || split_part(spot, '_', 2)
                    || case when split_part(spot, '_', 1) = 'drip' then '_up' else '_down' end
            end as relative_position,
            nullif(ml, '') as ml,
            nullif(ec, '') as ec,
            nullif(ph, '') as ph,
            nullif(temperature, '') as temperature,
            nullif(room, '') as room,
            -- free text: trimmed, null only when blank
            nullif(trim(remarks), '') as remarks,
            -- the csv has no bench: every measurement is at bench 4 for now
            '4' as bench
        from {{ source("dw_bronze", "brnz_journal_entries") }}
        -- the open load only (landed or accepted): there is at most one, so every data test judges it alone
        where load_id in ({{ loads_in_state(["landed", "accepted"]) }})
    ),

    assign_absolute_position as (
        -- the place, such as 1.30_4_front_left_up:
        -- - null when a part is null, so not_null fails
        -- - a combination that does not exist fails the relationships test
        -- - room, bench and relative_position are dropped by cast_select, which keeps only the yml's columns
        select *, room || '_' || bench || '_' || relative_position as absolute_position from mapped
    )

    {{ cast_select("assign_absolute_position") }}
