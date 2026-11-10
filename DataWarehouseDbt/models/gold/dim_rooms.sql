-- publishes ref_rooms, with a contract so gold presents checked types; its data tests are in ref_rooms.yml
select room, room_time, floor_number, assigned_stage, benches_number
from {{ ref("ref_rooms") }}
