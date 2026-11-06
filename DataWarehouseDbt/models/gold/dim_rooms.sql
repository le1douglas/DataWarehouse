-- the seed as a view with a contract, so gold presents it with checked types; its data tests are in the yml
select * from {{ ref("seed_rooms") }}
