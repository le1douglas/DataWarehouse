-- the seed as a table with a contract: a seed cannot have constraints, so they are declared on this model
select * from {{ ref("seed_rooms") }}
