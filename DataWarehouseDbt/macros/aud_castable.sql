{#
    true when a column is declared with a time zone
#}
{% macro is_timestamptz(col) %}
    {{ return((col.data_type | lower).startswith("timestamptz")) }}
{% endmacro %}

{#
    the condition that a value of col can be cast to the data_type its silver column declares. a timestamptz value
    must also end in a time zone that cannot be misread, right after the time: Z, an offset (+02, +0200, +02:00),
    UTC or a name with a slash (Europe/Amsterdam). without one, ::timestamptz would take the session's zone, and an
    abbreviation (CST, IST) can mean more than one zone.
    null when the value is null, so an empty value passes
#}
{% macro castable(col) %}
    {%- set name = adapter.quote(col.name) %}
    {%- if is_timestamptz(col) -%}
        (pg_input_is_valid({{ name }}, '{{ col.data_type }}')
        and {{ name }} ~ '[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)? ?(Z|[+-]\d{2}(:?\d{2})?|UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+)+)$')
    {%- else -%}
        pg_input_is_valid({{ name }}, '{{ col.data_type }}')
    {%- endif %}
{% endmacro %}

{#
    the body of aud_<dataset>__castable: the candidate rows with a value that cannot be cast to the data_type its
    silver column declares, so silver's unguarded casts never fail. an empty value is null and passes:
    pg_input_is_valid of null is null.
    returns row_id and description, the columns that cannot be cast separated by ", " (concat_ws skips the nulls).
    silver's yml is read from the graph, not with ref, so the test does not depend on silver
#}
{% macro aud_castable(dataset) %}
select
    row_id,
    concat_ws(
        ', '
        {%- for col in silver_columns(dataset) %}
        , case when not {{ castable(col) }} then '{{ col.name }}' end
        {%- endfor %}
    ) as description
from {{ ref("cand_" ~ dataset) }}
where
    {%- for col in silver_columns(dataset) %}
    {{ "or " if not loop.first }}not {{ castable(col) }}
    {%- endfor %}
{% endmacro %}
