{#
    the rows of the latest load whose columns equal another row, of the same load or of slvr_<dataset>: what silver will
    hold after this load, checked as one set. a row of silver with the same unique_key as a row of the load is about to
    be replaced by delete+insert, so it is left out: a batch sent again unchanged is not a clash with its own older
    version. a null never equals anything, so a row with a null in columns is left to its not_null test.
    silver is read from the graph, not with ref: a ref would run this test after silver, when the rows are already
    replaced. before silver's table exists, only the load is checked.
    the test runs on stg_<dataset>, and reads the dataset from that name. a dataset without silver is a mistake in the yml
#}
{% test unique_in_load_and_silver(model, columns) %}
    {# the graph is empty while dbt parses: silver_node stays none, and the test is a placeholder #}
    {% set silver_name = "slvr_" ~ model.identifier.removeprefix("stg_") if execute else none %}
    {% set silver_node = graph.nodes.get("model." ~ project_name ~ "." ~ silver_name) if execute else none %}

    {% if execute and (silver_node is none or not silver_node.config.unique_key) %}
        {{
            exceptions.raise_compiler_error(
                "unique_in_load_and_silver on "
                ~ model.identifier
                ~ ": "
                ~ silver_name
                ~ " has not been found or has no unique_key"
            )
        }}
    {% endif %}

    {% set silver = (
        adapter.get_relation(silver_node.database, silver_node.schema, silver_node.alias)
        if silver_node
        else none
    ) %}
    {# unique_key is a list, or a single column name #}
    {% set unique_key = silver_node.config.unique_key if silver_node else [] %}
    {% set unique_key = [unique_key] if unique_key is string else unique_key %}

    with
        -- what silver holds after the load: the load, and the rows of silver it does not replace
        after_load as (
            select row_id, {{ columns | join(", ") }}
            from {{ model }}
            {% if silver is not none %}
                union all
                select kept.row_id, {% for column in columns %} kept.{{ column }}{{ ", " if not loop.last }}{% endfor %}
                from {{ silver }} as kept
                where
                    not exists (
                        select
                        from {{ model }} as replacing
                        where
                            {%- for column in unique_key %}
                                {{ "and " if not loop.first }}replacing.{{ column }} = kept.{{ column }}
                            {%- endfor %}
                    )
            {% endif %}
        )

    -- each failing row once, however many rows it clashes with
    select latest.*
    from {{ model }} as latest
    where
        exists (
            select
            from after_load as other
            where
                latest.row_id <> other.row_id
                {%- for column in columns %} and latest.{{ column }} = other.{{ column }} {%- endfor %}
        )
{% endtest %}
