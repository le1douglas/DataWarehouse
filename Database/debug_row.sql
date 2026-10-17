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
-- the dataset the row belongs to: PIPELINE finds each layer's table as <prefix>_<dataset>
SET debug.dataset = 'journal_entries';

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
-- the row in every layer, one row per column and one column per layer, so it works for any dataset without naming
-- its columns. a column a layer does not have is null in it. a layer with no table for the dataset is left out.
-- every column is cast to text before query_to_xml sees it, so a value shows as ::TEXT shows it (a timestamptz in
-- the session's TimeZone), not in xml's format.
WITH layers AS (
    SELECT t.table_schema, t.table_name, l.layer_order, l.layer
    FROM (
        VALUES
            (1, 'bronze', 'dev_bronze', 'brnz'),
            (2, 'staging', 'dev_staging', 'stg'),
            (3, 'corrections', 'dev_corrections', 'corr'),
            (4, 'candidate', 'dev_candidate', 'cand'),
            (5, 'silver', 'dev_silver', 'slvr')
    ) AS l (layer_order, layer, schema_name, prefix)
    JOIN information_schema.tables AS t
        ON t.table_schema = l.schema_name AND t.table_name = l.prefix || '_' || current_setting('debug.dataset')
),

-- every layer's row as (column, value) pairs, in the layer's own column order. query_to_xml runs a query built as
-- text, which is the only way to read a table whose name is in a variable without creating a function. the query
-- selects every column of the table cast to text, its list read from information_schema
cells AS (
    SELECT l.layer_order, l.layer, x.column_order, x.column_name, x.value, x.is_null
    FROM layers AS l
    CROSS JOIN LATERAL xmltable(
        '/row/*'
        PASSING query_to_xml(
            format(
                'SELECT %s FROM %I.%I WHERE row_id = %L::UUID',
                (
                    SELECT string_agg(
                        format('%I::TEXT AS %I', c.column_name, c.column_name), ', ' ORDER BY c.ordinal_position
                    )
                    FROM information_schema.columns AS c
                    WHERE c.table_schema = l.table_schema AND c.table_name = l.table_name
                ),
                l.table_schema, l.table_name, current_setting('debug.row_id')
            ),
            TRUE, TRUE, ''
        )
        COLUMNS
            column_order FOR ORDINALITY,
            column_name TEXT PATH 'local-name()',
            value TEXT PATH '.',
            is_null BOOLEAN PATH 'boolean(@*[local-name() = "nil"])'
    ) AS x
)

-- bronze's columns first in bronze's order, then each column a later layer adds, in that layer's order
SELECT
    column_name,
    MAX(CASE WHEN NOT is_null THEN value END) FILTER (WHERE layer = 'bronze') AS bronze,
    MAX(CASE WHEN NOT is_null THEN value END) FILTER (WHERE layer = 'staging') AS staging,
    MAX(CASE WHEN NOT is_null THEN value END) FILTER (WHERE layer = 'corrections') AS corrections,
    MAX(CASE WHEN NOT is_null THEN value END) FILTER (WHERE layer = 'candidate') AS candidate,
    MAX(CASE WHEN NOT is_null THEN value END) FILTER (WHERE layer = 'silver') AS silver
FROM cells
GROUP BY column_name
ORDER BY MIN(layer_order * 1000 + column_order);





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

