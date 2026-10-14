-- the staged journal entries: picks and renames the columns, auto-fix rules, split of notes.
-- the column names and order of silver, all text except row_id: every column is cast in silver, after the
-- corrections, so a value that cannot be cast can still be corrected
with
    source as (
        select
            -- the key, assigned by bronze. it is carried through every step unchanged
            row_id, date_time, subject, notes, type, ec, ph, temp, tags as room_raw
        from {{ source("dev_bronze", "brnz_journal_entries") }}

    ),

    -- auto-fix rules: trim, empty becomes NULL, decimal comma becomes dot, harmonize date_time.
    auto_fixed as (
        select
            row_id,
            -- date_time gets the shape of the corrections, YYYY-MM-DD HH:MM:SS (T becomes a space and it is cut to the
            -- whole second).
            -- bronze always has the form 2026-09-17T15:13:08.363212 (or with fewer decimals), so the result always has
            -- the shape and it is not tested. no time zone here: it is only assigned in silver
            regexp_replace(replace(nullif(trim(date_time), ''), 'T', ' '), '\.\d+$', '') as date_time,
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
