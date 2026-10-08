-- all the mecahnincal steps: auto-fix rules, then casts.
-- same column names and types as corrections, except for the meta_ columns
-- the columns that are cast to numeric
{% set numeric_columns = ["ml", "ec", "ph", "temp"] %}

with
    source as (
        select
            -- the key: date_time cut to the second plus subject.
            -- the cast is not guarded: a date_time that is not a timestamp fails the whole build
            -- no time zone here: it is only assigned in silver
            date_trunc('second', date_time::timestamp)::timestamp(0) as date_time,
            subject,
            notes,
            type,
            ec,
            ph,
            temp,
            tags as room,
            meta_extract_date_time,
            meta_source
        from {{ source("dev_bronze", "brnz_journal_entries") }}

    ),

    -- auto-fix rules: trim, empty becomes NULL, decimal comma becomes dot
    auto_fixed as (
        select
            date_time,
            subject,
            nullif(trim(notes), '') as notes,
            nullif(trim(type), '') as type,
            replace(nullif(trim(ec), ''), ',', '.') as ec,
            replace(nullif(trim(ph), ''), ',', '.') as ph,
            replace(nullif(trim(temp), ''), ',', '.') as temp,
            nullif(trim(room), '') as room,
            meta_extract_date_time,
            meta_source
        from source

    ),

    -- split numbers and text in notes
    notes_split as (
        select
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
            room,
            meta_extract_date_time,
            meta_source
        from auto_fixed

    ),

    -- guarded casts: a value that cannot be cast becomes NULL and is reported in meta_cast_errors
    casted as (
        select
            date_time,
            subject,
            type,
            {%- for col in numeric_columns %}
                case when pg_input_is_valid({{ col }}, 'numeric') then {{ col }}::numeric end as {{ col }},
            {%- endfor %}
            notes,
            room,
            meta_extract_date_time,
            meta_source,
            nullif(
                concat_ws(
                    ', ',
                    {%- for col in numeric_columns %}
                        case
                            when not pg_input_is_valid({{ col }}, 'numeric') then '{{ col }}: ''' || {{ col }} || ''''
                        end{{ "," if not loop.last }}
                    {%- endfor %}
                ),
                ''
            ) as meta_cast_errors
        from notes_split

    )

select *
from casted
