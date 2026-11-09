{#
    the rows whose bench is not between 1 and the benches_number of their room in seed_rooms. the whole row is
    returned, so its row_id reaches aud_issues. a null bench is left to not_null, a room not in seed_rooms to its
    relationships test
#}
{% test bench_within_room(model, column_name) %}
    select model_rows.*
    from {{ model }} as model_rows
    inner join {{ ref("seed_rooms") }} as rooms on model_rows.room = rooms.room
    where model_rows.{{ column_name }} < 1 or model_rows.{{ column_name }} > rooms.benches_number
{% endtest %}
