{#
    the rows of the latest load whose key is already in slvr_<dataset> under another row_id: silver's delete+insert
    replaces those rows with these. meant as a warning, so every override is listed in elementary. the key is silver's
    own unique_key, so this lists exactly what silver replaces.
    silver is read from the graph, not with ref: a ref would run this test after silver, when the old rows are already
    replaced. before silver's table exists, nothing is replaced.
    the test runs on stg_<dataset>, and reads the dataset from that name. a dataset without silver is a mistake in the yml
#}
{% test unique_across_accepted_uploads(model) %}
    {# a warning, not a refusal: a newer upload overrides the older row in silver, and this lists it #}
    {{ config(severity="warn", meta={"description": "this key is already present in silver"}) }}
    {# the graph is empty while dbt parses: silver_node stays none, and the test is a placeholder #}
    {% set silver_name = "slvr_" ~ model.identifier.removeprefix("stg_") if execute else none %}
    {% set silver_node = graph.nodes.get("model." ~ project_name ~ "." ~ silver_name) if execute else none %}

    {% if execute and (silver_node is none or not silver_node.config.unique_key) %}
        {{ exceptions.raise_compiler_error("unique_across_accepted_uploads on " ~ model.identifier ~ ": " ~ silver_name ~ " has not been found or has no unique_key") }}
    {% endif %}

    {% set silver =adapter.get_relation(silver_node.database, silver_node.schema, silver_node.alias) if silver_node else none %}

    {% if silver is none %}
        select * from {{ model }} where false
    {% else %}
        select latest.*, replaced.row_id as replaced_row_id
        from {{ model }} as latest
        inner join {{ silver }} as replaced
            on
            {%- for column in silver_node.config.unique_key %}
                {{ "and " if not loop.first }}latest.{{ column }} = replaced.{{ column }}
            {%- endfor %}
        where latest.row_id <> replaced.row_id
    {% endif %}
{% endtest %}
