-- the meta table of staging: the metadata that staging decided, for every dataset of the layer.
-- one row per cast error, whether or not the row has a correction: a later layer decides if it still matters.
-- a table, not a view like the rest of the folder: its contract (meta_staging.yml) has a primary key and a foreign key
{{ config(materialized="table") }}

-- one call per dataset, joined with union all
{{ failed_casts("journal_entries") }}
