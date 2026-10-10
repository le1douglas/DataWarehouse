{#
    creates the audit view of every candidate model: aud_<dataset>, its flagged rows once, with the data tests each row
    failed in meta_failed_tests. it runs as an on-run-end hook (see dbt_project.yml).

    the view is not a dbt model, for two reasons (docs/adr/0001):
    - a model cannot depend on data tests, so dbt could not build it after them
    - dbt-postgres drops every failure table with cascade when its data test starts, and that drops any view on top
      of it. the view would disappear on every build, so it is created again here, after every run
#}
{% macro create_audit_views() %}
    {# the graph is only filled when dbt executes, not when it parses the project #}
    {% if not execute %} {{ return("") }} {% endif %}

    {# a data test belongs to the candidate model it references: the grouping comes from the graph, not from names #}
    {% set tests_by_model = {} %}
    {% for node in graph.nodes.values() | sort(attribute="name") %}
        {% if node.resource_type == "model" and node.fqn[1] == "candidate" %}
            {% do tests_by_model.update({node.unique_id: []}) %}
        {% endif %}
    {% endfor %}

    {% for test in graph.nodes.values() | sort(attribute="name") %}
        {% if test.resource_type == "test" %}
            {% set model_ids = [] %}
            {% for unique_id in test.depends_on.nodes %}
                {% if unique_id.startswith("model.") %} {% do model_ids.append(unique_id) %} {% endif %}
            {% endfor %}

            {% if model_ids | length == 0 %}
                {% do warn_left_out_of_audit_view(test, "it does not reference a model") %}
            {% elif model_ids | length > 1 %}
                {% do warn_left_out_of_audit_view(test, "it references more than one model") %}
            {% elif model_ids[0] not in tests_by_model %}
                {% do warn_left_out_of_audit_view(
                    test, "it references " ~ graph.nodes[model_ids[0]].name ~ ", which is not in the candidate folder"
                ) %}
            {% else %} {% do tests_by_model[model_ids[0]].append(test) %}
            {% endif %}
        {% endif %}
    {% endfor %}

    {% set statements = [] %}
    {% for model_id, tests in tests_by_model.items() %}
        {% set model = graph.nodes[model_id] %}
        {% set candidate = api.Relation.create(database=model.database, schema=model.schema, identifier=model.alias) %}
        {# columns are read from the database and not through adapter.get_relation: dbt does not add the failure
           tables to its relation cache, so the cache does not know the ones created in this run #}
        {% set candidate_columns = adapter.get_columns_in_relation(candidate) %}

        {# no columns means the candidate has not been built yet, there is nothing to shape the view on #}
        {% if candidate_columns | length > 0 %}
            {# a data test goes in the view when its failure table holds whole candidate rows #}
            {% set failure_tables = [] %}
            {% for test in tests %}
                {% set failure_table = api.Relation.create(
                    database=test.database, schema=test.schema, identifier=test.alias
                ) %}
                {% set failure_columns = adapter.get_columns_in_relation(failure_table) %}
                {% if failure_columns | length > 0 %}
                    {% if get_column_signature(failure_columns) == get_column_signature(candidate_columns) %}
                        {# the rule is the part of the name after the first __, or the whole name without one #}
                        {% do failure_tables.append({"relation": failure_table, "rule": test.name.split("__", 1) | last}) %}
                    {% else %}
                        {% do warn_left_out_of_audit_view(
                            test, "its failure table does not have the columns of " ~ model.name
                        ) %}
                    {% endif %}
                {# no failure table: the data test has never run, which is not worth a warning, or it never will #}
                {% elif test.config.store_failures == false %}
                    {% do warn_left_out_of_audit_view(test, "it does not store its failures") %}
                {% endif %}
            {% endfor %}

            {# the audit view takes the name of the model, with the audit prefix in place of the model's own #}
            {% set audit_view = api.Relation.create(
                database=model.database,
                schema=generate_schema_name("audit", model) | trim,
                identifier="aud_" ~ model.name.split("_", 1) | last,
                type="view",
            ) %}
            {% set column_list = candidate_columns | map(attribute="quoted") | join(", ") %}

            {% set statement %}
                create schema if not exists {{ audit_view.without_identifier().include(database=False) }};
                drop view if exists {{ audit_view }};
                create view {{ audit_view }} as
                {% if failure_tables | length > 0 %}
                    with
                        failures as (
                            {% for failure_table in failure_tables %}
                                select {{ column_list }}, '{{ failure_table.rule }}'::text as meta_failed_test
                                from {{ failure_table.relation }}
                                {{ "union all" if not loop.last }}
                            {% endfor %}
                        )
                    -- one row per flagged row: grouping on every column needs no knowledge of the key
                    select
                        {{ column_list }},
                        string_agg(meta_failed_test, ', ' order by meta_failed_test) as meta_failed_tests
                    from failures
                    group by {{ column_list }}
                {% else %}
                    -- no failure table yet: the view still exists, with the same columns and no rows
                    select {{ column_list }}, null::text as meta_failed_tests
                    from {{ candidate }}
                    where false
                {% endif %};
            {% endset %}
            {% do statements.append(statement) %}
        {% endif %}
    {% endfor %}

    {# dbt runs the statements it gets back, as it does for every on-run-end hook #}
    {{ return(statements | join("\n")) }}
{% endmacro %}


{# names and types of the columns, sorted, to compare two relations whatever the order of their columns #}
{% macro get_column_signature(columns) %}
    {% set signature = [] %}
    {% for column in columns %} {% do signature.append(column.name ~ " " ~ column.data_type) %} {% endfor %}
    {{ return(signature | sort) }}
{% endmacro %}


{# a data test that is not in the audit view is named on every run, a reviewer cannot see its failures in Excel #}
{% macro warn_left_out_of_audit_view(test, reason) %}
    {% do exceptions.warn("Data test " ~ test.name ~ " is left out of the audit view: " ~ reason ~ ".") %}
{% endmacro %}
