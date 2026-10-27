-- the staged journal entries: picks and renames the columns, auto-fix rules, split of notes.
-- the column names and order of silver, all text except row_id: every column is cast in silver, after the
-- corrections, so a value that cannot be cast can still be corrected
with
    source as (
        select
            -- the key, assigned by bronze. it is carried through every step unchanged
            row_id, date_time, subject, notes, type, ec, ph, temp, tags as room_raw
        from {{ source("dw_bronze", "brnz_journal_entries") }}

    ),

    -- auto-fix rules: trim, empty becomes NULL, decimal comma becomes dot, time zone of date_time.
    auto_fixed as (
        select
            row_id,
            -- date_time stays the text of the source, with a time zone written: when it ends right after the time
            -- (2026-09-17T15:13:08.363212), none is written and the timezone var is appended
            -- (2026-09-17T15:13:08.363212 Europe/Amsterdam). a name, not an offset such as +02:00: the offset changes
            -- with daylight saving (+02:00 in summer, +01:00 in winter), so writing it would mean working it out for
            -- each date. the name leaves that to the cast in silver. the time starts after T or a space, so an offset
            -- such as +02:00 is not taken for one. anything else is left as it is, a zone or not: whether it can be
            -- cast, and with a zone that cannot be misread, is the castable test's job
            case
                when trim(date_time) ~ '[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$'
                then trim(date_time) || ' {{ var("timezone") }}'
                else nullif(trim(date_time), '')
            end as date_time,
            subject,
            nullif(trim(notes), '') as notes,
            nullif(trim(type), '') as type,
            replace(nullif(trim(ec), ''), ',', '.') as ec,
            replace(nullif(trim(ph), ''), ',', '.') as ph,
            replace(nullif(trim(temp), ''), ',', '.') as temp,
            nullif(trim(room_raw), '') as room_raw
        from source

    ),

    -- split numbers and text in notes
    notes_split as (
        select
            row_id,
            date_time,
            subject,
            type,
            -- leading number only; NULL when notes doesn't start with one
            replace(substring(notes from '^(\d+(?:[.,]\d+)?)'), ',', '.') as ml,
            ec,
            ph,
            temp,
            -- text left over after the number; empty becomes NULL
            nullif(trim(regexp_replace(notes, '^\d+(?:[.,]\d+)?', '')), '') as notes,
            room_raw
        from auto_fixed

    )

select row_id, date_time, subject, type, ml, ec, ph, temp, notes, room_raw
from notes_split
