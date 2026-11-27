-- staging's accepted load, unchanged (select_accepted_loads)
-- - a row replaces the one with the same unique_key: the newest load wins, even an old file sent again
{{ select_accepted_loads(ref("stg_journal_entries")) }}
