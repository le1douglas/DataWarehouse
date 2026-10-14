-- the published journal entries: typed and derived columns only, no text copies and no helper columns.
-- everything that can go wrong happens in cand_journal_entries, this is rebuilt only when its tests pass
-- up to candidate the datetimes have no time zone, here they are all assigned to {{ var("timezone") }}
-- up to candidate the measurements are text, here they are cast. the cast is not guarded: the castable test on
-- candidate has already checked every value
select
    row_id,
    (date_time at time zone '{{ var("timezone") }}')::timestamptz(0) as date_time,
    subject,
    type,
    {%- for col in var("journal_entries_numeric_columns") %} {{ col }}::numeric as {{ col }}, {%- endfor %}
    notes,
    room_filled as room,
    "position"
from {{ ref("cand_journal_entries") }}
