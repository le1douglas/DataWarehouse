{#
    elementary's relationships_with_context, with a condition on the parent: the rows whose column_name is not among
    the field values of the rows of to that match to_condition, such as a room that is not a flowering room in
    ref_rooms. every failing row is returned whole, so its row_id reaches aud_issues. dbt_utils.relationships_where
    has the condition but returns only the value, and elementary's test returns the row but has no condition
#}
{% test relationships_where_with_context(model, column_name, to, field, to_condition) %}
    select child.*
    from {{ model }} as child
    left join (select {{ field }} from {{ to }} where {{ to_condition }}) as parent
        on child.{{ column_name }} = parent.{{ field }}
    where child.{{ column_name }} is not null and parent.{{ field }} is null
{% endtest %}
