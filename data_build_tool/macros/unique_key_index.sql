{#
    post-hook of every silver model: a plain index on unique_key, so the delete of each load is fast
    - not unique: a duplicate key is reported by the staging data tests, not refused by postgres
    - recreated when unique_key changes in slvr_<dataset>.yml; otherwise only the catalog is read
#}
{% macro unique_key_index() %}
    {# dbt renders hooks while it parses too, before the config is complete #}
    {% if execute %}
        {% set unique_key = config.get("unique_key") %}

        {% if not unique_key %}
            {{ exceptions.raise_compiler_error("unique_key_index: " ~ this.identifier ~ " has no unique_key") }}
        {% endif %}

        {# unique_key is a list, or a single column name #}
        {% set columns = [unique_key] if unique_key is string else unique_key %}
        {% set index_name = this.identifier ~ "_unique_key_idx" %}

        {# the existing index's columns, in order: empty when there is none #}
        {% set existing_query %}
            select attribute.attname
            from pg_index as index_
            inner join pg_class as index_class on index_class.oid = index_.indexrelid
            cross join unnest(index_.indkey) with ordinality as key_(attnum, position)
            inner join
                pg_attribute as attribute
                on attribute.attrelid = index_.indrelid
                and attribute.attnum = key_.attnum
            where index_class.relname = '{{ index_name }}'
                and index_class.relnamespace = '{{ this.schema }}'::regnamespace
            order by key_.position
        {% endset %}
        {% set existing = run_query(existing_query).columns[0].values() | list %}

        {% if existing != columns %}
            drop index if exists {{ this.schema }}.{{ index_name }};
            create index {{ index_name }} on {{ this }} ({{ columns | join(", ") }})
        {% else %}
            {# the index already matches, but a hook must run something #}
            select 1
        {% endif %}
    {% endif %}
{% endmacro %}
