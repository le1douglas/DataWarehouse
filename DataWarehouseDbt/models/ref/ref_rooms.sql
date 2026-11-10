-- the growing rooms, from seed_rooms. room is text, dbt infers the other types (dbt_project.yml)
select room, room_time, floor_number, assigned_stage, benches_number
from {{ ref("seed_rooms") }}
