-- the journal entries as a fact: one row per measurement, keyed by row_id, with a key to each dimension and the
-- measures. silver is already at this grain, so nothing is joined or derived. a view, so it always equals silver
select
    row_id,
    date_time,
    device,
    room,
    drip_or_drain,
    side,
    ml,
    ec,
    ph,
    temperature
from {{ ref("slvr_journal_entries") }}
