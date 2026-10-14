-- silver casts every column without a guard, so a value that cannot be cast to its type in
-- slvr_<dataset>.yml must stop it here
{{ aud_castable("journal_entries") }}
