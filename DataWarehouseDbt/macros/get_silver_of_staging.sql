{#
    the silver model of a staging model: stg_<dataset> gives slvr_<dataset>. returns its graph node, its relation in
    the database (none before silver's table exists) and its unique_key, always as a list. a staging model without
    silver, or a silver yml without unique_key, is a mistake in the yml.
    the graph is empty while dbt parses: this returns none, and the caller's test is a placeholder
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
