-- the proposed silver: corrections applied, then derived columns.
-- it has no meta_ columns: the cast errors are in meta_staging__failed_casts, and meta_corrections says which
-- rows are corrected
-- all the datetimes are without time zone, the time zone is only assigned in silver
-- the tests run on this view, silver is rebuilt only when all of them pass
-- the positions that are recorded, in the order they recorded in
{% set positions = ["drip_left", "drip_right", "drain_left", "drain_right"] %}

-- the columns that a correction replaces, they have the same name and type in staging and corrections
{% set correctable_columns = ["date_time", "subject", "type", "ml", "ec", "ph", "temp", "notes", "room"] %}

with
    staged as (select * from {{ ref("stg_journal_entries__cast") }}),

    corrections as (select * from {{ source("dev_corrections", "corr_journal_entries") }}),

    -- a correction replaces all the correctable columns of the row with the same row_id
    combined as (
        select
            s.row_id,
            {%- for col in correctable_columns %}
                case when c.row_id is not null then c.{{ col }} else s.{{ col }} end as {{ col }}
                {{- "," if not loop.last }}
            {%- endfor %}
        from staged as s
        left join corrections as c on s.row_id = c.row_id
    ),

    -- date_time and subject are not unique, row_id at the end of every ordering keeps the order of ties stable
    identify_room_entry_index as (
        select
            *,
            -- goes down the list in date_time order and increments every time it hits a room that is not null
            count(room) over (order by date_time, subject, row_id) as room_entry_index
        from combined
    ),

    carry_room as (
        select
            *,
            -- the room sits on the first row of its room_entry_index, copy it down so every row knows the room it is
            -- in.
            -- this is the only place where the room is copied down
            first_value(room) over (partition by room_entry_index order by date_time, subject, row_id) as room_carried
        from identify_room_entry_index
    ),

    flag_new_room_group as (
        select
            *,
            -- a room group starts on a row whose room is not null and is different from the room of the row before it.
            -- a row that repeats the room it is already in stays in the same room group
            (
                room is not null and room is distinct from lag(room_carried) over (order by date_time, subject, row_id)
            ) as is_new_room_group
        from carry_room
    ),

    identify_room_index as (
        select
            *,
            -- goes down the list in date_time order and increments every time a new room group starts
            count(*) filter (where is_new_room_group) over (order by date_time, subject, row_id) as room_index
        from flag_new_room_group
    ),

    -- TODO DEAL WITH ROOM WITH LESS THAN 3 positions
    identify_position_index as (

        select
            *,
            -- counts the rows inside each room_index
            row_number() over (partition by room_index order by date_time, subject, row_id) as position_index
        from identify_room_index

    ),

    assign_position as (
        select
            *,
            -- positions above positions.size keep cycling, which is why it uses %
            -- (a room group that has spilled in the next one, because its room is missing, still has the correct
            -- positions)
            -- Postgres arrays are 1-based, so row 1 maps to element 1
            (array[{%- for p in positions %}'{{ p }}'{{ "," if not loop.last }} {%- endfor %}])[
                (position_index - 1) % {{ positions | length }} + 1
            ] as "position"
        from identify_position_index

    ),

    assign_room as (
        select
            *,
            -- every row already carries the room of its room group,
            -- keep it only for the first positions.size rows; everything after stays null
            case when position_index <= {{ positions | length }} then room_carried end as room_filled
        from assign_position

    )

select
    row_id,
    {%- for col in correctable_columns %} {{ col }}, {%- endfor %}
    room_filled,
    room_index,
    position_index,
    "position"
from assign_room
