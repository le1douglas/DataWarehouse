select room, room_time, floor_number, assigned_stage, benches_total
from {{ ref("ref_rooms") }}
order by room_time, floor_number