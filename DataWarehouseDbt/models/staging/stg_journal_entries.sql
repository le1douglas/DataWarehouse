-- the staged journal entries: picks and renames the columns, auto-fix rules, split of notes.
-- the column names and order of silver, all text except date_time: the measurements are cast in silver, after the
-- corrections, so a value that cannot be cast can still be corrected
with
    source as (
        select
            -- the key, assigned by bronze. it is carried through every step unchanged
            row_id,
            -- date_time is cut to the second.
            -- the cast is not guarded: a date_time that is not a timestamp fails the whole build
            -- no time zone here: it is only assigned in silver
            date_trunc('second', date_time::timestamp)::timestamp(0) as date_time,
            subject,
            notes,
            type,
            ec,
            ph,
            temp,
            tags as room
        from {{ source("dev_bronze", "brnz_journal_entries") }}

    ),

    -- auto-fix rules: trim, empty becomes NULL, decimal comma becomes dot
    auto_fixed as (
        select
            row_id,
            date_time,
            subject,
            nullif(trim(notes), '') as notes,
            nullif(trim(type), '') as type,
            replace(nullif(trim(ec), ''), ',', '.') as ec,
            replace(nullif(trim(ph), ''), ',', '.') as ph,
            replace(nullif(trim(temp), ''), ',', '.') as temp,
            nullif(trim(room), '') as room
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
            room
        from auto_fixed

    )

select row_id, date_time, subject, type, ml, ec, ph, temp, notes, room
from notes_split
