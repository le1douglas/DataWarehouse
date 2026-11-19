-- ref_absolute_positions with the attributes of its room and relative position, so a fact needs only
-- absolute_position
with
    -- the floor of the room
    assign_floor_number as (
        select absolute_positions.*, rooms.floor_number
        from {{ ref("ref_absolute_positions") }} as absolute_positions
        inner join {{ ref("ref_rooms") }} as rooms on absolute_positions.room = rooms.room
    ),

    -- where on the bench: depth, horizontal and vertical
    split_relative_position as (
        select
            assign_floor_number.*, relative_positions.depth, relative_positions.horizontal, relative_positions.vertical
        from assign_floor_number
        inner join
            {{ ref("ref_relative_positions") }} as relative_positions
            on assign_floor_number.relative_position = relative_positions.relative_position
    )

select absolute_position, room, floor_number, bench, depth, horizontal, vertical
from split_relative_position
order by room, bench, depth, horizontal, vertical
