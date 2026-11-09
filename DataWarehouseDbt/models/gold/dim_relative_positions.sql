-- the reference data published to gold, with a contract so it presents checked types; its data tests are in the yml
select relative_position, depth, horizontal, vertical 
from {{ ref("seed_relative_positions") }} 
order by depth, vertical
