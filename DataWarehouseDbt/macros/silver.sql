{#
    the columns of slvr_<dataset> as declared in its yml, in their order, except row_id: the columns that silver
    casts from the text of the candidate. the yml is the only place their types are declared, the contract checks them.
    returns a list of column objects (name, data_type), empty while dbt parses.
    used by silver_select (below) and by aud_castable (macros/aud_castable.sql)
#}
{% macro silver_columns(dataset) %}
    {% if not execute %} {{ return([]) }} {% endif %}

    {% set silver_node = graph.nodes.get("model." ~ project_name ~ ".slvr_" ~ dataset) %}
    {{ return(silver_node.columns.values() | rejectattr("name", "equalto", "row_id") | list) }}
{% endmacro %}

{#
    true when a column is declared with a time zone. its text has none, so silver assigns var("timezone") to it and
    the castable test checks it as a timestamp without zone.
    used by silver_select (below) and by aud_castable (macros/aud_castable.sql)
#}
{% macro is_timestamptz(col) %}
    {{ return((col.data_type | lower).startswith("timestamptz")) }}
{% endmacro %}


{#
    the select of slvr_<dataset>: row_id unchanged, every other column of its yml cast from the candidate to its
    data_type. a timestamptz column first gets the time zone var("timezone"), the same rule for every dataset.
    the casts are not guarded: aud_<dataset>__castable has already checked every value.
    a candidate column that is not in the yml is not published.
    used by the silver models (models/silver/slvr_<dataset>.sql)
#}
{% macro silver_select(dataset) %}
select
    row_id
    {%- for col in silver_columns(dataset) %}
        {%- set name = adapter.quote(col.name) %}
        {%- set value = "(" ~ name ~ "::timestamp at time zone '" ~ var("timezone") ~ "')" if is_timestamptz(col) else name %}
    , {{ value }}::{{ col.data_type }} as {{ name }}
    {%- endfor %}
from {{ ref("cand_" ~ dataset) }}
{% endmacro %}
