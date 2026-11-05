-- every issue of every run: a failed or warned data test (one row per failing row), a data test that could not run, and
-- a model, snapshot or seed that errored. a failure of the whole file has no stored row with a row_id, so its row_id is
-- null. the message of a failed or warned data test is its meta.description, an error's is the database's.
-- the load is the load_id var of the run, so a failure of the whole file still says which load it was
with
    test_issues as (
        select
            results.invocation_id,
            results.status,
            regexp_replace(results.table_name, '^[^_]+_', '') as dataset,
            (result_rows.result_row::jsonb ->> 'row_id')::uuid as row_id,
            results.test_short_name as kind,
            results.column_name as target_column,
            case when results.status = 'error' then results.test_results_description else tests.description end
                as description
        from {{ ref("elementary", "elementary_test_results") }} as results
        inner join {{ ref("elementary", "dbt_tests") }} as tests on results.test_unique_id = tests.unique_id
        left join
            {{ ref("elementary", "test_result_rows") }} as result_rows
            on results.id = result_rows.elementary_test_results_id
        where results.status in ('fail', 'warn', 'error')
    ),

    node_errors as (
        select
            invocation_id,
            status,
            regexp_replace(name, '^[^_]+_', '') as dataset,
            null::uuid as row_id,
            resource_type as kind,
            null as target_column,
            message as description
        from {{ ref("elementary", "dbt_run_results") }}
        where status = 'error' and resource_type in ('model', 'snapshot', 'seed')
    ),

    issues as (
        select * from test_issues
        union all
        select * from node_errors
    )

select
    issues.invocation_id,
    (invocations.invocation_vars::jsonb ->> 'load_id')::uuid as load_id,
    issues.status,
    issues.dataset,
    issues.row_id,
    issues.kind,
    issues.target_column,
    issues.description
from issues
left join
    {{ ref("elementary", "dbt_invocations") }} as invocations
    on issues.invocation_id = invocations.invocation_id
