{#
    the type of a column is declared once, on the column of stg_<dataset>__cast in stg_<dataset>.yml:
    meta: {guarded_cast: <type>}. the macros in this file read the declarations, so the casts and their reporting
    follow from the yml and a dataset does not repeat them. both read the text values of stg_<dataset>.
#}
{# the select list of stg_<dataset>__cast: every column of the yml, in the order of the yml. a column with a
   guarded_cast is cast, and a value that cannot be cast becomes null. the others are selected as they are #}
{% macro guarded_casts(dataset) %}
    {% for column in get_declared_columns("stg_" ~ dataset ~ "__cast") %}
        {% set type = column.meta.get("guarded_cast") %}
        {% if type %}
            case
                when pg_input_is_valid({{ column.name }}, '{{ type }}') then {{ column.name }}::{{ type }}
            end as {{ column.name }}
        {% else %} {{ column.name }}
        {% endif %}
        {{ "," if not loop.last }}
    {% endfor %}
{% endmacro %}


{# the cast errors of a dataset, as rows of meta_staging: one row per value that is not null and cannot be cast to
   the type of its column. it reads the same text values as the casts, from stg_<dataset> #}
{% macro failed_casts(dataset) %}
    {# the ref stays outside any execute check: dbt finds dependencies while parsing, when execute is false #}
    {% set staged = ref("stg_" ~ dataset) %}

    {% set blocks = [] %}
    {% for column in get_declared_columns("stg_" ~ dataset ~ "__cast") %}
        {% set type = column.meta.get("guarded_cast") %}
        {% if type %}
            {% set block %}
                select
                    row_id,
                    'failed_cast'::varchar(50) as kind,
                    (
                        'failed to cast ''' || {{ column.name }} || ''' to {{ type }} on column {{ column.name }}'
                    )::varchar(400) as description
                from {{ staged }}
                where {{ column.name }} is not null and not pg_input_is_valid({{ column.name }}, '{{ type }}')
            {% endset %}
            {% do blocks.append(block) %}
        {% endif %}
    {% endfor %}

    {% if blocks | length > 0 %} {{ blocks | join("\nunion all\n") }}
    {# a dataset without a guarded cast has no cast errors: the same columns and no rows #}
    {% else %}
        select row_id, null::varchar(50) as kind, null::varchar(400) as description
        from {{ staged }}
        where false
    {% endif %}
{% endmacro %}


{# the columns of a model as they are declared in its yml, in the order of the yml #}
{% macro get_declared_columns(model_name) %}
    {# the graph is only filled when dbt executes, not when it parses the project #}
    {% if not execute %} {{ return([]) }} {% endif %}

    {% set node = graph.nodes.get("model." ~ project_name ~ "." ~ model_name) %}
    {% if node is none or node.columns | length == 0 %}
        {% do exceptions.raise_compiler_error("Model " ~ model_name ~ " has no columns declared in a yml file.") %}
    {% endif %}
    {{ return(node.columns.values() | list) }}
{% endmacro %}
