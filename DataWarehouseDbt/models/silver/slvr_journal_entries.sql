-- the published journal entries, generated from slvr_journal_entries.yml: every column is cast to its declared type.
-- everything that can go wrong happens in cand_journal_entries, this is rebuilt only when its tests pass.
-- dbt stops a model on a failed test only if the model depends on everything the test reads, so a test that also
-- reads dim_rooms needs this line
-- depends_on: {{ ref("dim_rooms") }}
{{ silver_select("journal_entries") }}
