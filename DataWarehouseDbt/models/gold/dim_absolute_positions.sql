-- publishes ref_absolute_positions, flattened: the attributes of the room and of the relative position are columns
-- here, so a fact needs only absolute_position. a contract so it presents checked types; its data tests are in
-- ref_absolute_positions.yml
select
    absolute_positions.absolute_position,
    absolute_positions.room,
    rooms.floor_number,
    absolute_positions.bench,
    relative_positions.depth,
    relative_positions.horizontal,
    relative_positions.vertical
from {{ ref("ref_absolute_positions") }} as absolute_positions
inner join {{ ref("ref_rooms") }} as rooms on absolute_positions.room = rooms.room
inner join
    {{ ref("ref_relative_positions") }} as relative_positions
    on absolute_positions.relative_position = relative_positions.relative_position
order by
    absolute_positions.room,
    absolute_positions.bench,
    relative_positions.depth,
    relative_positions.horizontal,
    relative_positions.vertical
