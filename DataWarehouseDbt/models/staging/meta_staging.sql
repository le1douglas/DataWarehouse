-- the meta table of staging: the metadata that staging decided, for every dataset of the layer.
-- one row per journal entry: the date_time it first reached staging, written once and never updated, like
-- extract_date_time in meta_bronze. a build only adds the row_ids that are not here yet.
-- the cast errors are not here: they are computed again on every read, see meta_staging__failed_casts
-- incremental, not a view like the rest of the folder: it keeps its rows between builds, and its contract
-- (meta_staging.yml) has a primary key and a foreign key. dbt build --full-refresh stamps every row again
{{ config(materialized="incremental", incremental_strategy="append", on_schema_change="fail") }}

-- one select per dataset, joined with union all.
-- the description has the format of extract_date_time: no time zone, cut to the second
select
    row_id,
    'staging_date_time'::varchar(50) as kind,
    to_char(localtimestamp(0), 'YYYY-MM-DD HH24:MI:SS')::varchar(400) as description
from {{ ref("stg_journal_entries") }}
{% if is_incremental() %} where row_id not in (select row_id from {{ this }}) {% endif %}
