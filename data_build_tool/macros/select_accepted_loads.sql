{#
    the select of slvr_<dataset>: staging's rows, once airflow has marked its load accepted
    - staging holds one load at most, so every row belongs to that load
    - during the audit this selects nothing, so a dbt build run by hand never publishes the load
#}
{% macro select_accepted_loads(staging) %}
    select *
    from {{ staging }}
    where exists ({{ loads_in_state(["accepted"], staging.identifier[4:]) }})
{% endmacro %}
