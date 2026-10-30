{#
    notify_run_end(): the sql that tells postgres a dbt command has ended, run by on-run-end

    what it sends
    - a notify on the channel dbt_run_end, which any connection to the database can listen to (listen dbt_run_end)
    - the payload is json: invocation_id, the id of the run in dbt's logs and target/run_results.json, and command, the
      dbt command that ran (build, run, test, seed, snapshot). a listener that only cares about some commands filters
      on it

    when it is sent
    - at the end of every command that runs on-run-end, whatever its results: a failed test still rebuilds its failure
      table and the audit table, so the data may have changed either way
    - after the audit tables: it is the last hook in dbt_project.yml, so a listener reads the audit of this run
    - postgres delivers it when the hook's transaction commits, and only to connections listening at that moment
#}
{% macro notify_run_end() %}
    {% if not execute %} {{ return("") }} {% endif %}
    {% set payload = tojson({"invocation_id": invocation_id, "command": flags.WHICH}) %}
    {{ return("select pg_notify('dbt_run_end', '" ~ payload | replace("'", "''") ~ "')") }}
{% endmacro %}
