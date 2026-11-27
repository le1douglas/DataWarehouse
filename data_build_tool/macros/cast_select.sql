{#
    the columns of the model's yml, in order, without row_id
    - the staging yml is the only place types are declared
    - empty while dbt parses
#}
{% macro declared_columns() %}
    {% if not execute %} {{ return([]) }} {% endif %}

    {{ return(model.columns.values() | rejectattr("name", "equalto", "row_id") | list) }}
{% endmacro %}

{#
    whether col can be cast to its data_type (null when the value is null)
    a timestamptz must also be ISO and end in a zone that cannot be misread. postgres alone would accept:
    - 03/11/2026, read month first
    - yesterday, 24:00 and second 60
    - no zone, which takes the session's
    - an abbreviation (CST, IST), which can mean more than one zone
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
    the final select of stg_<dataset>: row_id unchanged, every other column cast to its declared type
    - a value that cannot be cast becomes null and fails not_null: every bad row is reported, not only the first
#}
{% macro cast_select(cte) %}
select
    row_id
    {%- for col in declared_columns() %}
        {%- set name = adapter.quote(col.name) %}
    , case when {{ castable(col) }} then {{ name }}::{{ col.data_type }} end as {{ name }}
    {%- endfor %}
from {{ cte }}
{% endmacro %}
