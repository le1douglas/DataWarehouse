-- the plants batches as a fact: one row per plants batch, keyed by pp_number, with a key to its room and its planned
-- timeline. silver is already at this grain: the join to dim_rooms only adds room_time, and the foreign key on room
-- guarantees a match, so the left join never drops or repeats a batch. silver's dates and whole numbers need no
-- reduction of precision
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
