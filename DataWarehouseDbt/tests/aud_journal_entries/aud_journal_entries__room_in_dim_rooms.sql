-- the foreign key of room to dim_rooms, as a test on candidate: a real one would break the reload of the seed,
-- and on silver a wrong room would be published before the test could stop it
select cand.row_id, 'room' as target_column, 'room ' || cand.room || ' is not in dim_rooms' as description
from {{ ref("cand_journal_entries") }} as cand
left join {{ ref("dim_rooms") }} as dim on cand.room = dim.room
where cand.room is not null and dim.room is null
