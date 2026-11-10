-- every place a journal entry can be measured at: one row per room, bench of that room and relative position, from the
-- highest level to the lowest. reference data generated from seed_rooms and seed_relative_positions, so a room added
-- to seed_rooms gets its benches here, from benches_number. the attributes stay in those two
with
    list_benches as (
        -- one row per bench of each room, numbered from 1 to its benches_number
        select room, generate_series(1, benches_number) as bench from {{ ref("seed_rooms") }}
    ),

    combine_relative_positions as (
        -- every bench at every relative position
        select list_benches.room, list_benches.bench, relative_positions.relative_position
        from list_benches
        cross join {{ ref("seed_relative_positions") }} as relative_positions
    )

select room || '_' || bench || '_' || relative_position as absolute_position, room, bench, relative_position
from combine_relative_positions
