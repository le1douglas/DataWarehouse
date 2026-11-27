{#
    every data test runs through elementary's materialization, which stores the rows it returns
    - only the root project can override a built-in materialization
#}
{% materialization test, default %} {% do return(elementary.materialization_test_default()) %} {% endmaterialization %}
