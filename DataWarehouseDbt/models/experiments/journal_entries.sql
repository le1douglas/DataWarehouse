

--the positions that are recorded, in the order they recorded in
{% set positions = ['drip_left', 'drip_right', 'drain_left', 'drain_right'] %}

with staged as (
    select   *
         from {{ ref('stg_journal_entries') }}
),

corrections as (
    select 
        *
    from {{ source('corrections', 'journal_entries') }}
),

combined as (
    select entry_id,
        date_time,
        subject,
        type,
        ml,
        ec, 
        ph,  
        temp,
        notes,
        room,   
        meta_extract_date_time,
        meta_source,
        meta_silver_date_time, 
        false as meta_is_corrected
    from staged s
    where not exists (select 1 from corrections c where c.entry_id = s.entry_id)
    union all
    select  entry_id,
        date_time,
        subject,
        type,
        ml,
        ec, 
        ph,  
        temp,
        notes,
        room,   
        meta_extract_date_time,
        meta_source,
        meta_silver_date_time ,
        true as meta_is_corrected
    from corrections c
),



identify_room_index as (
    select
        *,
        -- goes down the list in date_time order and increments every time it hits a new tag that is not null
        count(room) over (order by date_time) as room_index 
    from combined
),


--TODO DEAL WITH ROOM WITH LESS THAN 3 positions
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
        -- the room sits on the first row of its group and is guaranteed non-null,
        -- so copy it down, but only for the first positions.size rows; everything after stays null
        case
            when position_index <= {{ positions | length }}
            then  first_value(room) over (partition by room_index order by date_time) 
        end as room_filled
    from assign_position

),


final_table as (
    select
        a.date_time,
        a.subject,
        a.type,
        a.ml,
        a.ec, 
        a.ph,  
        a.temp,
        a.notes,
        a.room_filled as room,
        a.meta_extract_date_time,
        a.meta_source,
        a.meta_silver_date_time, 
        a.meta_is_corrected,
        c.meta_reviewed_by as meta_reviewed_by,
        c.meta_reviewed_date_time as meta_reviewed_date_time
    from assign_room a
    left join corrections c
        on c.entry_id = a.entry_id

)

select * from assign_room
