{#
    the columns of slvr_<dataset> as declared in its yml, in their order, except row_id: the columns that silver
    casts from the text of the candidate. the yml is the only place their types are declared, the contract checks them.
    returns a list of column objects (name, data_type), empty while dbt parses
#}
{% macro silver_columns(dataset) %}
    {% if not execute %} {{ return([]) }} {% endif %}

    {% set silver_node = graph.nodes.get("model." ~ project_name ~ ".slvr_" ~ dataset) %}
    {{ return(silver_node.columns.values() | rejectattr("name", "equalto", "row_id") | list) }}
{% endmacro %}

{#
    true when a column is declared with a time zone. its text has none, so silver assigns var("timezone") to it and
    the castable test checks it as a timestamp without zone
#}
{% macro is_timestamptz(col) %}
    {{ return((col.data_type | lower).startswith("timestamptz")) }}
{% endmacro %}
