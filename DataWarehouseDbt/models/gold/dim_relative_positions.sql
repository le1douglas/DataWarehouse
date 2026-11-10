-- publishes ref_relative_positions, with a contract so gold presents checked types; its data tests are in
-- ref_relative_positions.yml
select relative_position, depth, horizontal, vertical 
from {{ ref("ref_relative_positions") }} 
order by depth, vertical
