-- one row per plants batch, keyed by pp_number
-- - a dimension, not a fact: plants_number describes the batch
-- - silver is already at this grain: the join only adds room_time
-- - a left join: staging checked the room once, at load time, so a room removed from seed_rooms later would
--   otherwise drop the batch
select
    plants_batches.row_id,
    plants_batches.pp_number,
    plants_batches.room,
    rooms.room_time,
    plants_batches.strain,
    plants_batches.date_veg_start,
    plants_batches.date_flower_start,
    plants_batches.date_flower_end,
    plants_batches.plants_number
from {{ ref("slvr_plants_batches") }} as plants_batches
left join {{ ref("dim_rooms") }} as rooms on plants_batches.room = rooms.room
order by plants_batches.date_flower_start
