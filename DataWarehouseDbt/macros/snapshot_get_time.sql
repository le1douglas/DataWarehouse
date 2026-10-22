{#
    the time of a snapshot, with its time zone: meta_valid_from, meta_valid_to and meta_updated_at are timestamptz.
    replaces dbt-postgres's own, now()::timestamp without time zone, which is ambiguous in the repeated hour in
    october. dbt sets the type of these columns only when it creates a snapshot table: an existing table keeps its
    type until it is dropped and built again
#}
{% macro postgres__snapshot_get_time() -%}
    now()
{%- endmacro %}
