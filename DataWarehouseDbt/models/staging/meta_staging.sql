-- the meta table of staging: the metadata that staging decided, for every dataset of the layer. two kinds of rows:
-- one row per cast error, whether or not the row has a correction: the data test no_cast_errors decides if it still
-- matters.
-- one row per journal entry: the date_time it first reached staging, written once and never updated, like
-- extract_date_time in meta_bronze. a build only adds the row_ids that are not here yet.
-- incremental, not a view like the rest of the folder: it keeps the date_times between builds, and its contract
-- (meta_staging.yml) has a primary key and a foreign key. the cast errors are not kept: the pre_hook deletes them
-- and every build writes them again, so a changed type declaration does not leave old ones behind.
-- dbt build --full-refresh stamps every row again
{{
    config(
        materialized="incremental",
        incremental_strategy="append",
        on_schema_change="fail",
        pre_hook="{% if is_incremental() %} delete from {{ this }} where kind = 'failed_cast' {% endif %}",
    )
}}

-- one call and one select per dataset, joined with union all
{{ failed_casts("journal_entries") }}

union all

-- the description has the format of extract_date_time: no time zone, cut to the second
select
    row_id,
    'staging_date_time'::varchar(50) as kind,
    to_char(localtimestamp(0), 'YYYY-MM-DD HH24:MI:SS')::varchar(400) as description
from {{ ref("stg_journal_entries") }}
{% if is_incremental() %}
    where row_id not in (select row_id from {{ this }} where kind = 'staging_date_time')
{% endif %}
