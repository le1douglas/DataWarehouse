{#
    the unique index on a silver table's unique_key, run as a post-hook on every silver model (dbt_project.yml). the
    key is declared once, in the model's yml: it decides what a load replaces (delete+insert), the staging tests read
    it, and this makes postgres refuse a duplicate key whatever writes to the table. the index also makes the delete
    of every load fast. created once, with the table: after that it already exists and this does nothing.
    a silver model without unique_key is a mistake in the yml
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

        create unique index if not exists {{ this.identifier }}_unique_key on {{ this }} ({{ columns | join(", ") }})
    {% endif %}
{% endmacro %}
