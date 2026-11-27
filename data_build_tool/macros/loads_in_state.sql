{#
    the load_id of every load in one of states, such as ["landed", "accepted"]
    - dataset keeps the loads of one dataset; without it, of every dataset
    - use: where load_id in ({{ loads_in_state(["accepted"]) }})
#}
{% macro loads_in_state(states, dataset=none) %}
    select load_id
    from {{ source("dw_control", "ctl_loads") }}
    where state in ('{{ states | join("', '") }}') {% if dataset %} and source = '{{ dataset }}' {% endif %}
{% endmacro %}
