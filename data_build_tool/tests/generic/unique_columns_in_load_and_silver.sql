{#
    the rows of the load whose columns equal another row, of the load or of silver after the load
    - columns: column names or expressions with no table alias, such as the local day of date_time
    - rows of silver with the same unique_key are left out: the load replaces them
    - a null equals nothing, so it is left to not_null
    - silver is read from the graph, not ref: a ref would run the test after silver had replaced the rows
    - before silver's table exists, only the load is checked
#}
{% test unique_columns_in_load_and_silver(model, columns) %}
    {# none while dbt parses: the test is a placeholder #}
    {% set silver = get_silver_of_staging(model) %}
    {% set relation = silver.relation if silver else none %}
    {% set unique_key = silver.unique_key if silver else [] %}

    with
        -- the load's values, one numbered column per entry of columns
        load_values as (
            select row_id {%- for column in columns %}, {{ column }} as value_{{ loop.index }} {%- endfor %}
            from {{ model }}
        ),

        -- what silver holds after the load: the load, and the rows of silver it does not replace
        after_load as (
            select *
            from load_values
            {% if relation is not none %}
                union all
                select kept.row_id {%- for column in columns %}, {{ column }} as value_{{ loop.index }} {%- endfor %}
                from {{ relation }} as kept
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
            from load_values as mine
            join
                after_load as other on mine.row_id <> other.row_id
                {%- for column in columns %}
                    and mine.value_{{ loop.index }} = other.value_{{ loop.index }}
                {%- endfor %}
            where mine.row_id = latest.row_id
        )
{% endtest %}

{#
    unique_columns_in_load_and_silver on unique_key, read from slvr_<dataset>.yml, so it takes no columns
    - in practice it checks the load alone: a key already in silver is replaced, and warn_overwritten_rows lists it
#}
{% test unique_business_key_in_load_and_silver(model) %}
    {# none while dbt parses: the test is a placeholder #}
    {% set silver = get_silver_of_staging(model) %}

    {{ test_unique_columns_in_load_and_silver(model, silver.unique_key if silver else []) }}
{% endtest %}
