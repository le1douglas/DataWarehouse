{#
    the rows of the load whose unique_key is already in silver under another row_id: the rows silver will replace
    - silver is read from the graph, not ref: a ref would run the test after silver had replaced the rows
    - before silver's table exists, nothing is replaced
#}
{% test warn_overwritten_rows(model) %}
    {# a warning, never a refusal: replacing a row is allowed, this only lists it #}
    {{ config(severity="warn", meta={"description": "this row overwrites the row with the same key in silver"}) }}
    {# none while dbt parses: the test is a placeholder #}
    {% set silver = get_silver_of_staging(model) %}

    {% if silver is none or silver.relation is none %}
        select * from {{ model }} where false
    {% else %}
        select latest.*, replaced.row_id as replaced_row_id
        from {{ model }} as latest
        inner join {{ silver.relation }} as replaced
            on
            {%- for column in silver.unique_key %}
                {{ "and " if not loop.first }}latest.{{ column }} = replaced.{{ column }}
            {%- endfor %}
        where latest.row_id <> replaced.row_id
    {% endif %}
{% endtest %}
