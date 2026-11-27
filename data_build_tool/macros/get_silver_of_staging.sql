{#
    the silver of a staging model (stg_<dataset> gives slvr_<dataset>): its graph node, relation and unique_key
    - relation is none until silver's table exists
    - unique_key is always a list
    - none while dbt parses, since the graph is empty
#}
{% macro get_silver_of_staging(model) %}
    {% if not execute %} {{ return(none) }} {% endif %}

    {% if not model.identifier.startswith("stg_") %}
        {{ exceptions.raise_compiler_error("get_silver_of_staging: " ~ model.identifier ~ " is not a staging model") }}
    {% endif %}

    {% set silver_name = "slvr_" ~ model.identifier[4:] %}
    {% set node = graph.nodes.get("model." ~ project_name ~ "." ~ silver_name) %}

    {% if node is none or not node.config.unique_key %}
        {{
            exceptions.raise_compiler_error(
                model.identifier ~ ": " ~ silver_name ~ " has not been found or has no unique_key"
            )
        }}
    {% endif %}

    {# unique_key is a list, or a single column name #}
    {% set unique_key = node.config.unique_key %}

    {{
        return(
            {
                "node": node,
                "relation": adapter.get_relation(node.database, node.schema, node.alias),
                "unique_key": [unique_key] if unique_key is string else unique_key,
            }
        )
    }}
{% endmacro %}
