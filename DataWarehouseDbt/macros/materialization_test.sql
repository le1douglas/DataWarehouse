{#
    every data test runs through elementary's materialization, which stores the rows it returns in test_result_rows.
    dbt does not let a package override a built-in materialization, so the root project has to do it
#}
{% materialization test, default %}
    {% do return(elementary.materialization_test_default()) %}
{% endmaterialization %}
