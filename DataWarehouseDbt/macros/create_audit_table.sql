{#
    create_audit_table(dataset, results): the sql of aud_<dataset> in the audit schema, run by on-run-end

    what it holds
    - the shape of a meta table: row_id, kind, description, one row per row_id and failed rule
    - kind is the bare rule, the part of the test name after "__"; description is the reason the test returned
    - the key is (row_id, kind), the primary key pk_aud_<dataset>: each data test returns at most one row per row_id
    - the columns, types and constraints of the meta tables: uuid, varchar(50), varchar(400), all not null, and
      fk_aud_<dataset>_row_id to the dataset's bronze table
    - each failure table gets the primary key pk_<failure table> on row_id
    - no columns of the candidate: a reader joins row_id to the candidate
    - zero rows when nothing failed

    how it is built
    - the union of the failure tables, with no join to the candidate
    - dropped, created with its columns and constraints, then filled
    - a table, not a view: it holds the failures of the run the data tests judged, a later load shows after the next run
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
    {% set failure_keys = [] %}
    {% for test in tests %}
        {% set failure_table = api.Relation.create(database=test.database, schema=test.schema, identifier=test.alias) %}
        {# dbt creates the failure table without constraints, so its key is added here, after the test ran #}
        {% do failure_keys.append(
            "alter table " ~ failure_table ~ " add constraint pk_" ~ test.alias ~ " primary key (row_id);"
        ) %}
        {% do failures.append(
            "select row_id, '" ~ test.name[prefix | length:] ~ "'::text as kind, description from " ~ failure_table
        ) %}
    {% endfor %}

    {% set audit_table = api.Relation.create(
        database=tests[0].database, schema=tests[0].schema, identifier="aud_" ~ dataset
    ) %}

    {# the failure keys go first: a test that returns a row_id twice fails here, before the audit table is replaced #}
    {# the columns and constraints are those of the meta tables in the hand-written ddl, so a value that does not fit
       fails the run instead of being cut. a row_id is flagged at most once per rule #}
    {% set sql %}
        {{ failure_keys | join("\n") }}
        drop table if exists {{ audit_table }};
        create table {{ audit_table }} (
            row_id uuid not null,
            kind varchar(50) not null,
            description varchar(400) not null,
            constraint pk_aud_{{ dataset }} primary key (row_id, kind),
            constraint fk_aud_{{ dataset }}_row_id foreign key (row_id)
            references {{ source("dev_bronze", "brnz_" ~ dataset) }} (row_id)
        );
        insert into {{ audit_table }} (row_id, kind, description)
        {{ failures | join("\nunion all\n") }};
    {% endset %}

    {{ return(sql) }}
{% endmacro %}
