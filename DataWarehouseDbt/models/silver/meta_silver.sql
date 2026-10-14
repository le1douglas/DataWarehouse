-- the meta table of silver: the metadata that silver decided, for every dataset of the layer.
-- one row per journal entry: the date_time it was first published in silver, written once and never updated, like
-- extract_date_time in meta_bronze. a build only adds the row_ids that are not here yet.
-- a row that a later correction changes is published again with the same row_id, so it keeps its first date_time
-- incremental, not a table like the rest of the folder: it keeps its rows between builds.
-- dbt build --full-refresh stamps every row again
-- the rows are read from slvr_journal_entries, so a failing data test on candidate skips this model together with
-- silver: a row is stamped only once it is published
{{ config(materialized="incremental", incremental_strategy="append", on_schema_change="fail") }}

-- one select per dataset, joined with union all.
-- the description has the format of extract_date_time: no time zone, cut to the second
select
    row_id,
    'silver_date_time'::varchar(50) as kind,
    to_char(localtimestamp(0), 'YYYY-MM-DD HH24:MI:SS')::varchar(400) as description
from {{ ref("slvr_journal_entries") }}
{% if is_incremental() %} where row_id not in (select row_id from {{ this }}) {% endif %}
