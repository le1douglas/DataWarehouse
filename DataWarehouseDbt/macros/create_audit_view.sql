{#
    the audit view of a dataset, aud_<dataset> in the audit schema: every flagged row once, with the current columns
    of its candidate and meta_failed_tests, the rules it failed (alphabetical, separated by ", ").
    it is created by on-run-end, not by a model: dbt drops a failure table with cascade every time its data test runs,
    which would drop a view that reads it. it exists with zero rows when nothing failed.
    only row_id is read from the failure tables, the values come from the candidate, so a failure table written by an
    older candidate cannot break the view. the data tests are read from the project, not from the schema, so the
    failure table of a deleted data test is left out. the failure tables stay the source of truth.
    returns the sql, which the hook runs
#}
{% macro create_audit_view(dataset) %}
    {% if not execute %} {{ return("") }} {% endif %}

    {% set candidate_node = graph.nodes.get("model." ~ project_name ~ ".cand_" ~ dataset) %}
    {% set candidate = api.Relation.create(
        database=candidate_node.database, schema=candidate_node.schema, identifier=candidate_node.alias
    ) %}

    {# the data tests of the dataset, aud_<dataset>__<rule>, and the schema they store their failures in #}
    {% set prefix = "aud_" ~ dataset ~ "__" %}
    {% set tests = [] %}
    {% for node in graph.nodes.values() if node.resource_type == "test" and node.name.startswith(prefix) %}
        {% do tests.append(node) %}
    {% endfor %}
    {% if tests | length == 0 %} {{ return("") }} {% endif %}
    {% set audit_schema = tests[0].schema %}

    {# a data test that has not run yet has no failure table #}
    {% set existing = run_query(
        "select tablename from pg_tables where schemaname = '" ~ audit_schema ~ "'"
    ).columns[0].values() %}

    {% set blocks = [] %}
    {% for test in tests if test.alias in existing %}
        {% set failures = api.Relation.create(database=test.database, schema=audit_schema, identifier=test.alias) %}
        {% do blocks.append(
            "select row_id, '" ~ test.name[prefix | length:] ~ "'::text as rule from " ~ failures
        ) %}
    {% endfor %}

    {% set audit_view = api.Relation.create(
        database=candidate_node.database, schema=audit_schema, identifier="aud_" ~ dataset
    ) %}

    {% set sql %}
        create schema if not exists {{ adapter.quote(audit_schema) }};
        -- dropped and created again, not replaced: replace fails when the candidate has lost a column
        drop view if exists {{ audit_view }};
        create view {{ audit_view }} as
        {% if blocks | length > 0 %}
            with
                failures as ({{ blocks | join("\nunion all\n") }}),

                failed_tests as (
                    select row_id, string_agg(distinct rule, ', ' order by rule) as meta_failed_tests
                    from failures
                    group by row_id
                )

            select candidate.*, failed_tests.meta_failed_tests
            from {{ candidate }} as candidate
            join failed_tests on failed_tests.row_id = candidate.row_id
        {% else %}
            select candidate.*, null::text as meta_failed_tests
            from {{ candidate }} as candidate
            where false
        {% endif %};
    {% endset %}

    {{ return(sql) }}
{% endmacro %}
