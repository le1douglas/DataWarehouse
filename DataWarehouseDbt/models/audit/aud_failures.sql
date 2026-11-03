-- every failure of every run, one row per failing row. a failure of the whole file has no stored row with a row_id, so
-- its row_id is null. warnings are left out: they do not block. the message of a data test is its meta.description
select
    results.invocation_id,
    regexp_replace(results.table_name, '^[^_]+_', '') as dataset,
    (result_rows.result_row::jsonb ->> 'row_id')::uuid as row_id,
    results.test_short_name as kind,
    results.column_name as target_column,
    tests.description
from {{ ref("elementary", "elementary_test_results") }} as results
inner join {{ ref("elementary", "dbt_tests") }} as tests on results.test_unique_id = tests.unique_id
left join
    {{ ref("elementary", "test_result_rows") }} as result_rows
    on results.id = result_rows.elementary_test_results_id
where results.status = 'fail'
