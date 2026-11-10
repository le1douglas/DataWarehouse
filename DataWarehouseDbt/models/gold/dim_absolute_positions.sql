-- publishes ref_absolute_positions, normalized: a key to the room and to the relative position, whose attributes
-- are only in dim_rooms and dim_relative_positions. a contract so it presents checked types; its data tests are in
-- ref_absolute_positions.yml
select absolute_position, room, bench, relative_position
from {{ ref("ref_absolute_positions") }}
order by room, bench, relative_position
