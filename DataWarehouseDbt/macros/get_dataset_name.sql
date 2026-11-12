{#
    the dataset of a model: its name without the layer prefix, everything up to and including the first _.
    slvr_journal_entries and stg_journal_entries both give journal_entries. only the first part goes, so a snapshot,
    snap_slvr_journal_entries, gives slvr_journal_entries. a name without _ has no layer prefix, a mistake in its name
#}
{% macro get_dataset_name(model_name) %}
    {% if "_" not in model_name %}
        {{ exceptions.raise_compiler_error("get_dataset_name: " ~ model_name ~ " has no layer prefix") }}
    {% endif %}

    {{ return(model_name.split("_", 1)[1]) }}
{% endmacro %}
