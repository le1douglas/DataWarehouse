--the proposed silver: corrections applied, then derived columns.
--all the datetimes are without time zone, the time zone is only assigned in silver
--the tests run on this view, silver is rebuilt only when all of them pass


--the positions that are recorded, in the order they recorded in
{% set positions = ['drip_left', 'drip_right', 'drain_left', 'drain_right'] %}

--the columns that a correction replaces, they have the same name and type in staging and corrections
{% set correctable_columns = ['type', 'ml', 'ec', 'ph', 'temp', 'notes', 'room'] %}

with staged as (
    select   *
         from {{ ref('stg_journal_entries') }}
),

corrections as (
    select
        *
    from {{ source('corrections', 'journal_entries') }}
),

-- a correction replaces all the correctable columns of the row with the same key
combined as (
    select
        s.date_time,
        s.subject,
        {%- for col in correctable_columns %}
        case when c.subject is not null then c.{{ col }} else s.{{ col }} end as {{ col }},
        {%- endfor %}
        s.meta_extract_date_time,
        s.meta_source,
        -- a corrected row has no cast errors: its values come from corrections, that is already typed
        case when c.subject is null then s.meta_cast_errors end as meta_cast_errors,
        c.subject is not null as meta_is_corrected,
        c.meta_reviewed_by,
        c.meta_reviewed_date_time
    from staged s
    left join corrections c
        on c.date_time = s.date_time
        and c.subject = s.subject
),

identify_room_index as (
    select
        *,
        -- goes down the list in date_time order and increments every time it hits a new tag that is not null
        count(room) over (order by date_time, subject) as room_index
    from combined
),


--TODO DEAL WITH ROOM WITH LESS THAN 3 positions
identify_position_index as (

    select
        *,
        -- counts the rows inside each room_index
        row_number() over (partition by room_index order by date_time, subject) as position_index
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
        -- the room sits on the first row of its group and is guaranteed non-null,
        -- so copy it down, but only for the first positions.size rows; everything after stays null
        case
            when position_index <= {{ positions | length }}
            then  first_value(room) over (partition by room_index order by date_time, subject)
        end as room_filled
    from assign_position

)

select
    date_time,
    subject,
    {%- for col in correctable_columns %}
    {{ col }},
    {%- endfor %}
    room_filled,
    room_index,
    position_index,
    "position",
    meta_extract_date_time,
    meta_source,
    meta_cast_errors,
    meta_is_corrected,
    meta_reviewed_by,
    meta_reviewed_date_time
from assign_room
