-- the cast errors of staging, for every dataset of the layer: one row per value that cannot be cast, whether or not
-- the row has a correction: the data test no_cast_errors decides if it still matters.
-- a view like the rest of the folder: it is computed again on every read, so it always follows bronze and the type
-- declarations in the yml of each dataset. it is not metadata with a date, that is in meta_staging
-- one call per dataset, joined with union all
{{ failed_casts("journal_entries") }}

--union all
-- etc...
