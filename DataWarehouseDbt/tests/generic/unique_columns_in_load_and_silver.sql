{#
    the rows of the latest load whose columns equal another row, of the same load or of slvr_<dataset>: what silver will
    hold after this load, checked as one set. for any set of columns that must be unique together; the business key
    has its own test below.
    a row of silver with the same unique_key as a row of the load is about to be replaced by delete+insert, so it is
    left out: a batch sent again unchanged is not a clash with its own older version. a null never equals anything, so
    a row with a null in columns is left to its not_null test.
    silver is read from the graph, not with ref: a ref would run the test after silver, when the rows are already
    replaced. before silver's table exists, only the load is checked.
    the test runs on stg_<dataset>, and reads the dataset from that name. a dataset without silver, or a silver yml
    without unique_key, is a mistake in the yml
#}
{% test unique_columns_in_load_and_silver(model, columns) %}
    {# the graph is empty while dbt parses: silver is none, and the test is a placeholder #}
    {% set silver = get_silver_of_staging(model) %}
    {% set relation = silver.relation if silver else none %}
    {% set unique_key = silver.unique_key if silver else [] %}

    with
        -- what silver holds after the load: the load, and the rows of silver it does not replace
        after_load as (
            select row_id, {{ columns | join(", ") }}
            from {{ model }}
            {% if relation is not none %}
                union all
                select kept.row_id, {% for column in columns %} kept.{{ column }}{{ ", " if not loop.last }}{% endfor %}
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
            from after_load as other
            where
                latest.row_id <> other.row_id
                {%- for column in columns %} and latest.{{ column }} = other.{{ column }} {%- endfor %}
        )
{% endtest %}

{#
    unique_columns_in_load_and_silver on the business key: unique_key in slvr_<dataset>.yml, the only place it is
    declared, so this test takes no columns. silver's rows with the same key are the ones the load replaces, so in
    practice this checks the load alone: a duplicate within the load is an error, a key already in silver is an
    overwrite, listed by warn_overwritten_rows
#}
{% test unique_business_key_in_load_and_silver(model) %}
    {# the graph is empty while dbt parses: the key stays empty, and the test is a placeholder #}
    {% set silver = get_silver_of_staging(model) %}

    {{ test_unique_columns_in_load_and_silver(model, silver.unique_key if silver else []) }}
{% endtest %}
