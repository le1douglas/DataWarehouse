-- the journal entries as a fact: one row per measurement, keyed by row_id, with a key to each dimension and the
-- measures. silver is already at this grain, so nothing is joined. a view, so it always equals silver.
-- silver keeps the precision the csv sends, gold reduces it: date_time to the second, the decimals to 2
select
    row_id,
    -- truncated, not rounded: 23:59:59.7 stays on its day. the cast only declares the precision
    date_trunc('second', date_time)::timestamptz(0) as date_time,
    device,
    absolute_position,
    ml,
    -- the cast rounds half away from zero: 5.125 becomes 5.13. silver's ranges fit in numeric(4,2)
    ec::numeric(4, 2) as ec,
    ph::numeric(4, 2) as ph,
    temperature::numeric(4, 2) as temperature
from {{ ref("slvr_journal_entries") }}
