-- every place a journal entry can be measured at: one row per room, bench of that room and relative position, from the
-- highest level to the lowest. reference data generated from seed_rooms and seed_relative_positions, so a room added
-- to seed_rooms gets its benches here, from benches_number
with
    list_benches as (
        -- one row per bench of each room, numbered from 1 to its benches_number
        select room, floor_number, generate_series(1, benches_number) as bench from {{ ref("seed_rooms") }}
    ),

    combine_relative_positions as (
        -- every bench at every relative position
        select
            list_benches.room,
            list_benches.floor_number,
            list_benches.bench,
            relative_positions.relative_position,
            relative_positions.depth,
            relative_positions.horizontal,
            relative_positions.vertical
        from list_benches
        cross join {{ ref("seed_relative_positions") }} as relative_positions
    )

select
    room || '_' || bench || '_' || relative_position as absolute_position,
    floor_number,
    room,
    bench,
    relative_position,
    depth,
    horizontal,
    vertical
from combine_relative_positions
