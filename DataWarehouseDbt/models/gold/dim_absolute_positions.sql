-- the reference data published to gold, normalized: a key to the room and to the relative position, whose attributes
-- are only in dim_rooms and dim_relative_positions. a contract so it presents checked types; its data tests are in
-- the yml
select absolute_position, room, bench, relative_position
from {{ ref("seed_absolute_positions") }}
order by room, bench, relative_position
