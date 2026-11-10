-- the rooms a plants batch can be grown in: those whose assigned_stage is flowering. reference data generated from
-- seed_rooms, so a room changed there is changed here. a mother room never flowers, so it holds no plants batch
select room
from {{ ref("seed_rooms") }}
where assigned_stage = 'flowering'
