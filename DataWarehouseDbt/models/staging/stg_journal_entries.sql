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
            nullif(spot, '') as spot,
            nullif(ml, '') as ml,
            nullif(ec, '') as ec,
            nullif(ph, '') as ph,
            nullif(temperature, '') as temperature,
            nullif(room, '') as room
        from {{ source("dw_bronze", "brnz_journal_entries") }}
        -- one load only, the load_id var, so every data test judges that load alone. without the var, compilation fails
        where load_id = '{{ var("load_id") }}'::uuid
    )

    {{ cast_select("mapped", "journal_entries") }}
