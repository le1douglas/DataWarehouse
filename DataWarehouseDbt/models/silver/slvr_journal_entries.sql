-- the published journal entries: typed and derived columns only, no text copies and no helper columns.
-- everything that can go wrong happens in cand_journal_entries, this is rebuilt only when its tests pass
-- up to candidate the datetimes have no time zone, here they are all assigned to {{ var("timezone") }}
-- the data test no_cast_errors also reads the two relations below. dbt lets a data test stop a model only when the
-- model depends on everything the test reads, so they are named here although nothing is selected from them.
-- without these two lines a cast error does not keep silver from being built
-- depends_on: {{ ref("meta_staging") }}
-- depends_on: {{ source("dev_corrections", "meta_corrections") }}
select
    row_id,
    (date_time at time zone '{{ var("timezone") }}')::timestamptz(0) as date_time,
    subject,
    type,
    ml,
    ec,
    ph,
    temp,
    notes,
    room_filled as room,
    "position"
from {{ ref("cand_journal_entries") }}
