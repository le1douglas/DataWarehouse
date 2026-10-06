--all the mecahnincal steps:


with source as (
    select
        {{ dbt_utils.generate_surrogate_key(['date_time', 'subject']) }} as entry_id,
        date_time::timestamp at time zone '{{ var("timezone") }}' as date_time,
        subject::text,
        notes::text,
        type::text,
        ec::numeric,
        ph::numeric,
        temp::numeric,
        tags::text as room,
        meta_extract_date_time::timestamp at time zone '{{ var("timezone") }}' as meta_extract_date_time,
        meta_source::text,
        now() at time zone '{{ var("timezone") }}' as meta_silver_date_time
    from {{ source('bronze', 'journal_entries') }}

),


-- clean sensor name
subject_cleaned as (
    select
        entry_id,
        date_time,
        -- strip " - measurement" from the end, case-insensitive
        regexp_replace(subject, '\s*-\s*' || type || '\s*$', '', 'i') as subject,
        notes,
        type,
        ec,
        ph,
        temp,
        room,
        meta_extract_date_time,
        meta_source,
        meta_silver_date_time
    from source

),

--split numbers and text in notes
notes_split as (
    select
        entry_id,
        date_time,
        subject,
        -- leading number only; NULL when notes doesn't start with one
        substring(notes from '^\s*(\d+(?:\.\d+)?)')::numeric as ml,
        -- text left over after the number; empty becomes NULL
        nullif(trim(regexp_replace(notes, '^\s*\d+(?:\.\d+)?\s*', '')), '') as notes,
        type,
        ec,
        ph,
        temp,
        room,
        meta_extract_date_time,
        meta_source,
        meta_silver_date_time
    from subject_cleaned

)

select * from notes_split