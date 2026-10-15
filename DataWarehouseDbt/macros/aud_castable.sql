{#
    the body of aud_<dataset>__castable: the candidate rows with a value that cannot be cast to the data_type its
    silver column declares, so silver's unguarded casts never fail. an empty value is null and passes:
    pg_input_is_valid of null is null. a timestamptz column is checked as a timestamp, its text has no zone yet.
    returns row_id and description, the columns that cannot be cast separated by ", " (concat_ws skips the nulls).
    silver's yml is read from the graph, not with ref, so the test does not depend on silver
#}
{% macro aud_castable(dataset) %}
select
    row_id,
    concat_ws(
        ', '
        {%- for col in silver_columns(dataset) %}
            {%- set type = "timestamp" if is_timestamptz(col) else col.data_type %}
        , case when not pg_input_is_valid({{ adapter.quote(col.name) }}, '{{ type }}') then '{{ col.name }}' end
        {%- endfor %}
    ) as description
from {{ ref("cand_" ~ dataset) }}
where
    {%- for col in silver_columns(dataset) %}
        {%- set type = "timestamp" if is_timestamptz(col) else col.data_type %}
    {{ "or " if not loop.first }}not pg_input_is_valid({{ adapter.quote(col.name) }}, '{{ type }}')
    {%- endfor %}
{% endmacro %}
