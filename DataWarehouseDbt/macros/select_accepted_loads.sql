{#
    the select of slvr_<dataset>: staging, when the load it holds is accepted, that is passed its audit and not yet
    published (ctl_loads, see loads_in_state). every load run ends its load
    (DataWarehouseAirflow/dags/load_datasets.py), so staging holds one load at most, and when the dataset has an
    accepted load, every row of staging is that load. while the load is landed, under audit, this selects nothing: the
    gate is airflow's verdict, not dbt skipping silver after a failed test, so a dbt build run by hand during an audit
    never publishes the load. a refused or failed load is not in staging. its business key is unique, staging tests it
#}
{% macro select_accepted_loads(staging) %}
    select *
    from {{ staging }}
    where exists ({{ loads_in_state(["accepted"], staging.identifier[4:]) }})
{% endmacro %}
