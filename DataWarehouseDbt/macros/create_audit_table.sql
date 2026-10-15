{#
    create_audit_table(dataset, results): the sql of aud_<dataset> in the audit schema, run by on-run-end

    what it holds
    - every row flagged by a data test aud_<dataset>__<rule>, once
    - the columns of the candidate at the end of the run, plus meta_failed_tests: its rules, alphabetical, ", "
    - zero rows when nothing failed

    how it is built
    - row_id from the failure tables, every other value from the candidate
    - dropped and created again, so its columns follow the candidate
    - a table, not a view: its values are the ones the data tests judged, a later load shows after the next run
    - created in on-run-end, not as a model, because a model downstream of the candidate is skipped when a test fails

    when it is built
    - only when every data test of the dataset in the project ran to a pass or a fail in this run (results)
    - otherwise it is left as the copy of the last run where they all did: a test that was not selected, was
      skipped or errored keeps the failure table of an older run, and mixing runs would make the table wrong
    - a deleted data test is not in the project, so its leftover failure table is ignored
    - each dataset depends only on its own tests

    the failure tables stay the source of truth
#}
{% macro create_audit_table(dataset, results) %}
    {% if not execute %} {{ return("") }} {% endif %}

    {# the data tests of the dataset #}
    {% set prefix = "aud_" ~ dataset ~ "__" %}
    {% set tests = [] %}
    {% for node in graph.nodes.values() if node.resource_type == "test" and node.name.startswith(prefix) %}
        {% do tests.append(node) %}
    {% endfor %}
    {% if tests | length == 0 %} {{ return("") }} {% endif %}

    {# every one of them ran to a result in this run, so every failure table exists and is from this run #}
    {% set judged = [] %}
    {% for result in results if result.status in ["pass", "fail", "warn"] %}
        {% do judged.append(result.node.unique_id) %}
    {% endfor %}
    {% for test in tests if test.unique_id not in judged %} {{ return("") }} {% endfor %}

    {% set failures = [] %}
    {% for test in tests %}
        {% set failure_table = api.Relation.create(database=test.database, schema=test.schema, identifier=test.alias) %}
        {% do failures.append(
            "select row_id, '" ~ test.name[prefix | length:] ~ "'::text as rule from " ~ failure_table
        ) %}
    {% endfor %}

    {% set candidate_node = graph.nodes.get("model." ~ project_name ~ ".cand_" ~ dataset) %}
    {% set candidate = api.Relation.create(
        database=candidate_node.database, schema=candidate_node.schema, identifier=candidate_node.alias
    ) %}
    {% set audit_table = api.Relation.create(
        database=candidate_node.database, schema=tests[0].schema, identifier="aud_" ~ dataset
    ) %}

    {% set sql %}
        drop table if exists {{ audit_table }};
        create table {{ audit_table }} as
        with
            failures as ({{ failures | join("\nunion all\n") }}),

            failed_tests as (
                select row_id, string_agg(distinct rule, ', ' order by rule) as meta_failed_tests
                from failures
                group by row_id
            )

        select candidate.*, failed_tests.meta_failed_tests
        from {{ candidate }} as candidate
        join failed_tests on failed_tests.row_id = candidate.row_id;
    {% endset %}

    {{ return(sql) }}
{% endmacro %}
