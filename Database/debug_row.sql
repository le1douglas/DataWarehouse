-- the main metadata of one journal entry, each with a name a person can read: a short version of
-- debug_journal_entry.sql. paste a row_id in the SET below and run the whole file.
--
-- a query, not a database object, for the same reason as debug_journal_entry.sql. a fact with nothing for this
-- row_id adds no row.
-- the snapshot times assume a dbt build right after every load: a version is added only when a value changes, so
-- the newest meta_valid_from is since when the current values hold, not the last load or build. if the newest
-- version is deleted, it is when the row disappeared.

-- the row_id every query reads: a setting of this connection only, it writes nothing. run a query on its own in a
-- new connection and current_setting fails with "unrecognized configuration parameter"
SET debug.row_id = '01a13f97-1c47-7d10-b2d3-ad66d8386cd7';

-------------------------------------------------------------------------------


-- TIMELINE
-- timeline and basic metadata for every layer
WITH params AS (
    SELECT current_setting('debug.row_id')::UUID AS row_id
),

-- every fact the summary can show, named as in debug_journal_entry.sql
facts AS (
    SELECT 'meta_bronze' AS origin, m.kind::TEXT AS kind, m.description::TEXT AS description
    FROM dev_bronze.meta_bronze AS m
    JOIN params AS p ON m.row_id = p.row_id
    UNION ALL
    -- the row_id is a uuidv7 assigned on insert into bronze, so its timestamp is when the row was loaded
    SELECT 'meta_bronze', 'meta_bronze_load_date_time', uuid_extract_timestamp(b.row_id)::TEXT
    FROM dev_bronze.brnz_journal_entries AS b
    JOIN params AS p ON b.row_id = p.row_id
    UNION ALL
    SELECT 'meta_corrections', m.kind::TEXT, m.description::TEXT
    FROM dev_corrections.meta_corrections AS m
    JOIN params AS p ON m.row_id = p.row_id
    UNION ALL
    -- the newest version is the one with the latest meta_valid_from
    SELECT 'snap_meta_corrections', s.kind || '.newest.meta_valid_from', MAX(s.meta_valid_from)::TEXT
    FROM dev_snapshots.snap_meta_corrections AS s
    JOIN params AS p ON s.row_id = p.row_id
    GROUP BY s.kind
    UNION ALL
    SELECT 'snap_slvr_journal_entries', 'newest.meta_valid_from', MAX(s.meta_valid_from)::TEXT
    FROM dev_snapshots.snap_slvr_journal_entries AS s
    JOIN params AS p ON s.row_id = p.row_id
    GROUP BY s.row_id
),

-- the facts the summary shows, in this order, with their readable name
friendly_names AS (
    SELECT *
    FROM (
        VALUES
            (1, 'meta_bronze', 'meta_extract_date_time', 'extract date time'),
            (2, 'meta_bronze', 'meta_source', 'extract source'),
            (3, 'meta_bronze', 'meta_bronze_load_date_time', 'bronze insert date time'),
            (4, 'meta_corrections', 'meta_reviewed_date_time', 'reviewed date time'),
            (5, 'meta_corrections', 'meta_reviewed_by', 'reviewed by'),
            (6, 'snap_meta_corrections', 'meta_reviewed_date_time.newest.meta_valid_from', 'correction insert date time (latest version)'),
            (7, 'snap_slvr_journal_entries', 'newest.meta_valid_from', 'silver insert date time (latest version)')
    ) AS n (sort_order, origin, kind, friendly_name)
)

SELECT n.friendly_name, f.description, f.kind, f.origin
FROM facts AS f
JOIN friendly_names AS n ON f.origin = n.origin AND f.kind = n.kind
ORDER BY n.sort_order;





-- PIPELINE
-- the row in every layer, one below the other, all as text. a column a layer does not have is null in it.
SELECT layer, row_id, date_time, subject, type, ml, ec, ph, temp, notes, room_raw, room, room_index, position_index,
    "position", tags, ec_pore, ec_bulk, mc, device, media
FROM (
    SELECT
        1 AS layer_order, 'brnz_journal_entries' AS layer, b.row_id, b.date_time::TEXT AS date_time,
        b.subject::TEXT AS subject, b.type::TEXT AS type, NULL::TEXT AS ml, b.ec::TEXT AS ec, b.ph::TEXT AS ph,
        b.temp::TEXT AS temp, b.notes::TEXT AS notes, NULL::TEXT AS room_raw, NULL::TEXT AS room,
        NULL::TEXT AS room_index, NULL::TEXT AS position_index, NULL::TEXT AS "position", b.tags::TEXT AS tags,
        b.ec_pore::TEXT AS ec_pore, b.ec_bulk::TEXT AS ec_bulk, b.mc::TEXT AS mc, b.device::TEXT AS device,
        b.media::TEXT AS media
    FROM dev_bronze.brnz_journal_entries AS b
    WHERE b.row_id = current_setting('debug.row_id')::UUID
    UNION ALL
    SELECT
        2, 'stg_journal_entries', s.row_id, s.date_time, s.subject, s.type, s.ml, s.ec, s.ph, s.temp, s.notes,
        s.room_raw, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
    FROM dev_staging.stg_journal_entries AS s
    WHERE s.row_id = current_setting('debug.row_id')::UUID
    UNION ALL
    SELECT
        3, 'corr_journal_entries', c.row_id, c.date_time, c.subject, c.type, c.ml, c.ec, c.ph, c.temp, c.notes,
        c.room_raw, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
    FROM dev_corrections.corr_journal_entries AS c
    WHERE c.row_id = current_setting('debug.row_id')::UUID
    UNION ALL
    SELECT
        4, 'cand_journal_entries', c.row_id, c.date_time, c.subject, c.type, c.ml, c.ec, c.ph, c.temp, c.notes,
        c.room_raw, c.room, c.room_index::TEXT, c.position_index::TEXT, c."position", NULL, NULL, NULL, NULL, NULL,
        NULL
    FROM dev_candidate.cand_journal_entries AS c
    WHERE c.row_id = current_setting('debug.row_id')::UUID
    UNION ALL
    SELECT
        5, 'slvr_journal_entries', s.row_id, s.date_time::TEXT, s.subject, s.type, s.ml::TEXT, s.ec::TEXT, s.ph::TEXT,
        s.temp::TEXT, s.notes, NULL, s.room, NULL, NULL, s."position", NULL, NULL, NULL, NULL, NULL, NULL
    FROM dev_silver.slvr_journal_entries AS s
    WHERE s.row_id = current_setting('debug.row_id')::UUID
) AS layers
ORDER BY layer_order;





-- AUDIT
-- the rules failed in the last full build
SELECT a.*
FROM dev_audit.aud_journal_entries AS a
WHERE a.row_id = current_setting('debug.row_id')::UUID
ORDER BY a.kind;



-----------------------------------------------

-- BRONZE

SELECT b.*
FROM dev_bronze.brnz_journal_entries AS b
WHERE b.row_id = current_setting('debug.row_id')::UUID;

SELECT m.*
FROM dev_bronze.meta_bronze AS m
WHERE m.row_id = current_setting('debug.row_id')::UUID
ORDER BY m.kind;


-- STAGING

SELECT s.*
FROM dev_staging.stg_journal_entries AS s
WHERE s.row_id = current_setting('debug.row_id')::UUID;


-- CANDIDATE

SELECT c.*
FROM dev_candidate.cand_journal_entries AS c
WHERE c.row_id = current_setting('debug.row_id')::UUID;


-- CORRECTIONS

SELECT c.*
FROM dev_corrections.corr_journal_entries AS c
WHERE c.row_id = current_setting('debug.row_id')::UUID;

SELECT m.*
FROM dev_corrections.meta_corrections AS m
WHERE m.row_id = current_setting('debug.row_id')::UUID
ORDER BY m.kind;

-- every version, oldest first
SELECT s.*
FROM dev_snapshots.snap_corr_journal_entries AS s
WHERE s.row_id = current_setting('debug.row_id')::UUID
ORDER BY s.meta_valid_from;

-- every version of each kind, oldest first
SELECT s.*
FROM dev_snapshots.snap_meta_corrections AS s
WHERE s.row_id = current_setting('debug.row_id')::UUID
ORDER BY s.kind, s.meta_valid_from;


-- AUDIT

-- the rules failed in the last full build
SELECT a.*
FROM dev_audit.aud_journal_entries AS a
WHERE a.row_id = current_setting('debug.row_id')::UUID
ORDER BY a.kind;


-- SILVER

SELECT s.*
FROM dev_silver.slvr_journal_entries AS s
WHERE s.row_id = current_setting('debug.row_id')::UUID;

-- every version, oldest first
SELECT s.*
FROM dev_snapshots.snap_slvr_journal_entries AS s
WHERE s.row_id = current_setting('debug.row_id')::UUID
ORDER BY s.meta_valid_from;

