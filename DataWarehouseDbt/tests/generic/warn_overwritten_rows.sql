{#
    the rows of the latest load whose key is already in slvr_<dataset> under another row_id: silver's delete+insert
    replaces those rows with these. meant as a warning, so every override is listed in elementary. the key is silver's
    own unique_key, so this lists exactly what silver replaces.
    silver is read from the graph, not with ref: a ref would run this test after silver, when the old rows are already
    replaced. before silver's table exists, nothing is replaced.
    the test runs on stg_<dataset>, and reads the dataset from that name. a dataset without silver is a mistake in the yml
#}
{% test warn_overwritten_rows(model) %}
    {# only a warning, never a refusal: a newer load overwrites the older row in silver, and this lists it #}
    {{ config(severity="warn", meta={"description": "this row overwrites the row with the same key in silver"}) }}
    {# the graph is empty while dbt parses: silver is none, and the test is a placeholder #}
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
