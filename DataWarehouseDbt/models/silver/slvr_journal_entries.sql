-- the published journal entries, generated from slvr_journal_entries.yml: every column is cast to its declared type.
-- everything that can go wrong happens in cand_journal_entries, this is rebuilt only when its tests pass
{{ silver_select("journal_entries") }}
