-- the staged journal entries. the csv is written by a program of ours, so the only changes are empty to null and the
-- time zone: anything else is an upstream fault and fails a data test. the output is typed, see cast_select
with
    mapped as (
        select
            -- the key, assigned by bronze. it is carried through every step unchanged
            row_id,
            -- the csv writes date_time without a time zone, so the timezone var is appended. a name, not an offset such
            -- as +02:00: the offset changes with daylight saving, the cast works it out for each date
            -- TODO change so it gets the source timezone from the csv.
            nullif(date_time, '') || ' {{ var("timezone") }}' as date_time,
            nullif(device, '') as device,
            -- the csv sends spot as drip or drain and the side joined by _, such as drip_left. it becomes the relative
            -- position: always front, drip is up and drain is down, so drip_left is front_left_up. any other value is
            -- null here and fails not_null
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
            -- the csv has no bench: every measurement is taken at bench 4 for now. text like the other columns, so
            -- cast_select casts it
            '4' as bench
        from {{ source("dw_bronze", "brnz_journal_entries") }}
        -- one load only, the load_id var, so every data test judges that load alone. without the var, compilation fails
        where load_id = '{{ var("load_id") }}'::uuid
    )

    {{ cast_select("mapped", "journal_entries") }}
