-- the published journal entries. no logic: staging has cast them, and its yml declares the columns and types. the
-- rows of the accepted loads, see select_accepted_loads. incremental, as every silver model (dbt_project.yml): a row
-- replaces the row with the same business key (unique_key in slvr_journal_entries.yml), so a newer upload of a
-- measurement overrides the older one
{{ select_accepted_loads(ref("stg_journal_entries")) }}
