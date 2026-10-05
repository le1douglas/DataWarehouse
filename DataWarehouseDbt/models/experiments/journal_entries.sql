

--the positions that are recorded, in the order they recorded in
{% set positions = ['drip_left', 'drip_right', 'drain_left', 'drain_right'] %}

with source as (

    select
        date_time::timestamp at time zone 'Europe/Amsterdam' as date_time,
        subject::text,
        notes::text, --as of now it contains both ml and actual notes, numbers will be separated after and cast to the correct type
        type::text,
        ec::numeric,
        ph::numeric,
        temp::numeric,
        tags::text,
        meta_extract_date_time::timestamp at time zone 'Europe/Amsterdam' as meta_extract_date_time,
        meta_source::text
    from {{ source('bronze', 'journal_entries') }}

),

subject_cleaned as (

    select
        date_time,
        -- strip " - measurement" from the end, case-insensitive
        regexp_replace(subject, '\s*-\s*' || type || '\s*$', '', 'i') as subject,
        notes,
        type,
        ec,
        ph,
        temp,
        tags,
        meta_extract_date_time,
        meta_source
    from source

),

notes_split as (

    select
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
        tags,
        meta_extract_date_time,
        meta_source
    from subject_cleaned

),

identify_room_index as (
    select
        *,
        -- goes down the list in date_time order and increments every time it hits a new tag that is not null
        count(tags) over (order by date_time) as room_index 
    from notes_split
),


identify_position_index as (

    select
        *,
        -- counts the rows inside each room_index
        row_number() over (partition by room_index order by date_time) as position_index
    from identify_room_index

),
assign_position as (
    select
        *,
        -- positions above positions.size keep cycling,  (an untagged room that has spilled in the next room, still has the correct positions)
        -- which is why it uses %
        (array[
            {%- for p in positions %}
            '{{ p }}'{{ "," if not loop.last }}
            {%- endfor %}
        ])[(position_index - 1) % {{ positions | length }} + 1] as "position"   -- Postgres arrays are 1-based, so row 1 maps to element 1
    from identify_position_index

),

assign_room as (

    select
        *,
        -- the tag sits on the first row of its group and is guaranteed non-null,
        -- so copy it down, but only for the first positions.size rows; everything after stays null
        case
            when position_index <= {{ positions | length }}
            then first_value(tags) over (partition by room_index order by date_time)
        end as room
    from assign_position

),


final_table as (
    select
        date_time,
        subject,
        ml,
        notes,
        type,
        ec,
        ph,
        temp,
        room_index,
        room,
        position_index,
        position,
        meta_extract_date_time,
        meta_source
    from assign_room

) 

select * from final_table