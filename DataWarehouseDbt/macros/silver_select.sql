{#
    the select of slvr_<dataset>: row_id unchanged, every other column of its yml cast from the candidate to its
    data_type. a timestamptz column first gets the time zone var("timezone"), the same rule for every dataset.
    the casts are not guarded: aud_<dataset>__castable has already checked every value.
    a candidate column that is not in the yml is not published
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
