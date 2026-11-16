{#
    a subquery of the load_id of every load whose state is one of states, such as ["landed", "accepted"]: ctl_loads
    holds one row per load, its current state. dataset, such as journal_entries, keeps only the loads of that source;
    without it, every dataset's: load_ids are uuidv7, unique across datasets.
    for a filter, where load_id in ({{ loads_in_state(["accepted"]) }})
#}
{% macro loads_in_state(states, dataset=none) %}
    select load_id
    from {{ source("dw_control", "ctl_loads") }}
    where state in ('{{ states | join("', '") }}') {% if dataset %} and source = '{{ dataset }}' {% endif %}
{% endmacro %}
