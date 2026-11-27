-- room is text (dbt_project.yml): dbt would infer 1.30 as a number
select room, room_time, floor_number, assigned_stage, benches_total
from {{ ref("seed_rooms") }}
