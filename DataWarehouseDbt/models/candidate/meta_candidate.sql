-- the meta table of candidate: the metadata that candidate decided, for every dataset of the layer.
-- one row per journal entry: the date_time it first reached candidate, written once and never updated, like
-- extract_date_time in meta_bronze. a build only adds the row_ids that are not here yet.
-- a table, not a view like the rest of the folder: it keeps its rows between builds, and its contract
-- (meta_candidate.yml) has a primary key and a foreign key. dbt build --full-refresh stamps every row again
-- the rows are read from stg_journal_entries__cast, which has the same row_ids as cand_journal_entries. reading
-- candidate would let a failing data test skip this model, and a row that fails a test still passed through candidate
{{ config(materialized="incremental", incremental_strategy="append", on_schema_change="fail") }}

-- one select per dataset, joined with union all.
-- the description has the format of extract_date_time: no time zone, cut to the second
select
    row_id,
    'candidate_date_time'::varchar(50) as kind,
    to_char(localtimestamp(0), 'YYYY-MM-DD HH24:MI:SS')::varchar(400) as description
from {{ ref("stg_journal_entries__cast") }}
{% if is_incremental() %} where row_id not in (select row_id from {{ this }}) {% endif %}
