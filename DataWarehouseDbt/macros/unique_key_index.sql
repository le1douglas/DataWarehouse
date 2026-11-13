{#
    a plain index on a silver table's unique_key, run as a post-hook on every silver model (dbt_project.yml). the key
    is declared once, in slvr_<dataset>.yml: it decides what a load replaces (delete+insert), and the
    staging tests read it. the index only makes the delete of every load fast: a duplicate key is reported by the
    staging data tests, not refused by postgres.
    kept in step with unique_key on every load: created when it is missing, also on a table that existed before, and
    dropped and created again when its columns are no longer the unique_key's. otherwise only the catalog is read.
    postgres keeps its rows up to date by itself.
    a silver model without unique_key is a mistake in its yml
#}
{% macro unique_key_index() %}
    {# dbt also renders hooks while it parses, before the config is complete: the check waits for execution #}
    {% if execute %}
        {% set unique_key = config.get("unique_key") %}

        {% if not unique_key %}
            {{ exceptions.raise_compiler_error("unique_key_index: " ~ this.identifier ~ " has no unique_key") }}
        {% endif %}

        {# unique_key is a list, or a single column name #}
        {% set columns = [unique_key] if unique_key is string else unique_key %}
        {% set index_name = this.identifier ~ "_unique_key_idx" %}

        {# the columns of the existing index, in their order: an empty list when there is no index #}
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
            {# a hook must run something: the index already matches #}
            select 1
        {% endif %}
    {% endif %}
{% endmacro %}
