CREATE SCHEMA IF NOT EXISTS corrections

CREATE TABLE IF NOT EXISTS corrections.journal_entries (
    entry_id               TEXT PRIMARY KEY,
    date_time              TIMESTAMPTZ NOT NULL,
    subject                TEXT,
    type                   TEXT,
    ml                     NUMERIC,
    ec                     NUMERIC,
    ph                     NUMERIC,
    temp                   NUMERIC,
    notes                  TEXT,
    room                    TEXT,
    meta_extract_date_time TIMESTAMPTZ NOT NULL,
    meta_source            TEXT NOT NULL,
    meta_silver_date_time TIMESTAMPTZ NOT NULL,
    meta_reviewed_by            TEXT NOT NULL,
    meta_reviewed_date_time            TIMESTAMP NOT NULL
);

-- DROP TABLE corrections.journal_entries
