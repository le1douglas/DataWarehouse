{#
    elementary's relationships_with_context, with a condition on the parent, such as a flowering room in ref_rooms
    - returns the whole failing row, so its row_id reaches elementary's tables
    - dbt_utils.relationships_where has the condition, but returns only the value
#}
{% test relationships_where_with_context(model, column_name, to, field, to_condition) %}
    select child.*
    from {{ model }} as child
    left join (select {{ field }} from {{ to }} where {{ to_condition }}) as parent
        on child.{{ column_name }} = parent.{{ field }}
    where child.{{ column_name }} is not null and parent.{{ field }} is null
{% endtest %}
