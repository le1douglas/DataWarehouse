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
    the reason a value of col fails castable, for a reviewer: the column and the data_type it must be cast to
#}
{% macro castable_description(col) -%}
    column {{ col.name }} is not of type {{ col.data_type }}
{%- endmacro %}

{#
    the body of aud_<dataset>__castable: the candidate rows with a value that cannot be cast to the data_type its
    silver column declares, so silver's unguarded casts never fail. an empty value is null and passes:
    pg_input_is_valid of null is null.
    returns row_id, target_column and description: one row per value that cannot be cast, with the column it is in
    and its castable_description. each candidate row is unpivoted into one row per column by the lateral values, so
    the candidate is read once. silver's yml is read from the graph, not with ref, so the test does not depend on
    silver
#}
{% macro aud_castable(dataset) %}
select
    cand.row_id,
    checked.target_column,
    checked.description
from {{ ref("cand_" ~ dataset) }} as cand
cross join lateral (
    values
    {%- for col in silver_columns(dataset) %}
        ('{{ col.name }}', {{ castable(col) }}, '{{ castable_description(col) }}'){{ "," if not loop.last }}
    {%- endfor %}
) as checked (target_column, is_castable, description)
where not checked.is_castable
{% endmacro %}
