{#
    the columns of slvr_<dataset> as declared in its yml, in their order, except row_id. the yml is the only place their
    types are declared, the contract checks them. it is read from the graph, not with ref, so staging does not depend
    on silver. returns a list of column objects (name, data_type), empty while dbt parses
#}
{% macro silver_columns(dataset) %}
    {% if not execute %} {{ return([]) }} {% endif %}

    {% set silver_node = graph.nodes.get("model." ~ project_name ~ ".slvr_" ~ dataset) %}
    {{ return(silver_node.columns.values() | rejectattr("name", "equalto", "row_id") | list) }}
{% endmacro %}

{#
    the condition that a value of col can be cast to the data_type its silver column declares. a timestamptz value
    must also be ISO from its first character: yyyy-mm-dd, T or a space, an hour 00-23 and minutes and seconds 00-59.
    postgres would also read 03/11/2026 (month first), yesterday (the day of the build), 24:00 and second 60.
    it must end in a time zone that cannot be misread, right after the time: Z, an offset (+02, +0200, +02:00),
    UTC or a name with a slash (Europe/Amsterdam). without one, ::timestamptz would take the session's zone, and an
    abbreviation (CST, IST) can mean more than one zone.
    null when the value is null
#}
{% macro castable(col) %}
    {%- set name = adapter.quote(col.name) %}
    {%- if (col.data_type | lower).startswith("timestamptz") -%}
        (pg_input_is_valid({{ name }}, '{{ col.data_type }}')
        and {{ name }} ~ '^\d{4}-\d{2}-\d{2}[T ]([01]\d|2[0-3]):[0-5]\d(:[0-5]\d(\.\d+)?)? ?(Z|[+-]\d{2}(:?\d{2})?|UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+)+)$')
    {%- else -%}
        pg_input_is_valid({{ name }}, '{{ col.data_type }}')
    {%- endif %}
{% endmacro %}

{#
    the final select of stg_<dataset>: row_id unchanged, every other column of slvr_<dataset>.yml cast to its data_type.
    a value that cannot be cast becomes null and fails its not_null data test, so every bad row is reported, instead of
    the view crashing on the first
#}
{% macro cast_select(cte, dataset) %}
select
    row_id
    {%- for col in silver_columns(dataset) %}
        {%- set name = adapter.quote(col.name) %}
    , case when {{ castable(col) }} then {{ name }}::{{ col.data_type }} end as {{ name }}
    {%- endfor %}
from {{ cte }}
{% endmacro %}
