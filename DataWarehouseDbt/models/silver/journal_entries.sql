-- the published journal entries: typed and derived columns only, no text copies and no helper columns.
-- everything that can go wrong happens in cand_journal_entries, this is rebuilt only when its tests pass
-- up to candidate the datetimes have no time zone, here they are all assigned to {{ var("timezone") }}
select
    (date_time at time zone '{{ var("timezone") }}')::timestamptz(0) as date_time,
    subject,
    type,
    ml,
    ec,
    ph,
    temp,
    notes,
    room_filled as room,
    "position",
    meta_extract_date_time at time zone '{{ var("timezone") }}' as meta_extract_date_time,
    meta_source,
    now() as meta_silver_date_time,
    meta_is_corrected,
    meta_reviewed_by,
    meta_reviewed_date_time at time zone '{{ var("timezone") }}' as meta_reviewed_date_time
from {{ ref("cand_journal_entries") }}
