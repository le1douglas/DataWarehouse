-- every relative position: each value of depth combined with each of horizontal and of vertical. generated from
-- seed_relative_position_values, so a value added there makes its combinations here
with
    list_values as (select axis, value from {{ ref("seed_relative_position_values") }}),

    combine_axes as (
        -- every combination of one value per axis
        select depth.value as depth, horizontal.value as horizontal, vertical.value as vertical
        from list_values as depth
        cross join list_values as horizontal
        cross join list_values as vertical
        where depth.axis = 'depth' and horizontal.axis = 'horizontal' and vertical.axis = 'vertical'
    )

select depth || '_' || horizontal || '_' || vertical as relative_position, depth, horizontal, vertical
from combine_axes
