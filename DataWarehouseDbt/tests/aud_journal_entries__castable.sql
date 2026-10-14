{{ config(severity="error", store_failures=true) }}

-- silver casts every column without a guard, so a value that cannot be cast to its type in
-- slvr_journal_entries.yml must stop it here
{{ castable("journal_entries") }}
