{#
    the select list of every data test: the columns of a meta table, with the same types, so the failure tables can
    be combined with a plain union all. the description is the rule, read from the name of the test that calls the
    macro (aud_<dataset>__<rule>), so it is not typed a second time. the test selects one row per failing row_id
#}
{% macro failed_test_columns() %}
    {% set name_parts = model.name.split("__", 1) %}
    {% if name_parts | length < 2 %}
        {% do exceptions.raise_compiler_error(
            "Data test " ~ model.name ~ " has no rule in its name: expected aud_<dataset>__<rule>."
        ) %}
    {% endif %}
    row_id,
    'failed_test'::varchar(50) as kind,
    '{{ name_parts[1] }}'::varchar(400) as description
{% endmacro %}
