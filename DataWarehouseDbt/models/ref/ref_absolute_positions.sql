-- every place a journal entry can be measured: each room, bench and relative position
-- - generated, so a room added to seed_rooms gets its benches from benches_total
-- - the attributes stay in ref_rooms and ref_relative_positions
with
    list_benches as (
        -- one row per bench of each room
        select room, generate_series(1, benches_total) as bench from {{ ref("ref_rooms") }}
    ),

    combine_relative_positions as (
        -- every bench at every relative position
        select list_benches.room, list_benches.bench, relative_positions.relative_position
        from list_benches
        cross join {{ ref("ref_relative_positions") }} as relative_positions
    )

select room || '_' || bench || '_' || relative_position as absolute_position, room, bench, relative_position
from combine_relative_positions
