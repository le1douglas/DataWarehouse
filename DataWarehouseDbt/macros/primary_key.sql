{#
    the primary key of a silver table, run as a post-hook on every silver model (dbt_project.yml). the only constraint
    in silver: every other rule is a data test on staging. silver has no contract, so dbt does not create it.
    added once, with the table: after that the table already has a primary key and this does nothing
#}
{% macro primary_key(column) %}
    {# dbt also renders hooks while it parses: the statement waits for execution #}
    {% if execute %}
        do $$
        begin
            if not exists (
                select from pg_constraint
                where conrelid = '{{ this.schema }}.{{ this.identifier }}'::regclass and contype = 'p'
            ) then
                alter table {{ this }} add primary key ({{ column }});
            end if;
        end
        $$
    {% endif %}
{% endmacro %}
