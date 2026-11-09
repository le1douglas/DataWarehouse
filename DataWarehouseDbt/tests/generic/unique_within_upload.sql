{#
    the rows of the latest load that share slvr_<dataset>'s unique_key with another row of the same load. the key is
    declared once, in the silver yml,
    elementary's test does the work, so every failing row is reported with its context.
    a dataset without silver is a mistake in the yml
#}
{% test unique_within_upload(model, dataset) %}
    {# the graph is empty while dbt parses: silver_node stays none, and the test is a placeholder #}
    {% set silver_node = graph.nodes.get("model." ~ project_name ~ ".slvr_" ~ dataset) if execute else none %}

    {% if execute and (silver_node is none or not silver_node.config.unique_key) %}
        {{ exceptions.raise_compiler_error("unique_within_upload: slvr_" ~ dataset ~ " has not been found or has no unique_key") }}
    {% endif %}

    {% if silver_node is none %}
        select * from {{ model }} where false
    {% else %}
        {{ elementary.test_expect_compound_columns_to_be_unique_with_context(model, silver_node.config.unique_key) }}
    {% endif %}
{% endtest %}
