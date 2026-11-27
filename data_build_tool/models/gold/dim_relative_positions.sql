select relative_position, depth, horizontal, vertical 
from {{ ref("ref_relative_positions") }} 
order by depth, vertical
