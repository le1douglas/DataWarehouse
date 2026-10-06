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
SELECT * FROM corrections.journal_entries
TRUNCATE corrections.journal_entries



INSERT INTO corrections.journal_entries (
    entry_id, date_time, subject, type, ml, ec, ph, temp, notes, room,
    meta_extract_date_time, meta_source, meta_silver_date_time,
    meta_reviewed_by, meta_reviewed_date_time
) VALUES
('3afc3cd355ef371a172794a44c75df63', '2026-09-17 14:57:13.892601+02', 'ONE-A1F0', 'measurement', 1000, 1.37, 6.08, 21.9, NULL, '0.28',
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('72dd6cca468995f46c6c1e6b03cc2c52', '2026-09-17 14:57:20.858315+02', 'ONE-A1F0', 'measurement', 1000, 1.3, 6.15, 22, NULL, '0.28',
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('e7c1fcea03509d6dd3a60a6edbda45a9', '2026-09-17 14:57:34.845819+02', 'ONE-A1F0', 'measurement', 1400, 2.03, 6.29, 21.7, NULL, '0.28',
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('07e6680619459c89877295ab1049227c', '2026-09-17 14:57:43.423173+02', 'ONE-A1F0', 'measurement', 1400, 1.71, 6.61, 21.5, NULL, '0.28',
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('9f097350ea2069f12f56f1e0f590477f', '2026-09-17 15:08:12.795471+02', 'ONE-A1F0', 'measurement', 1700, 1.55, 6.38, 24.6, NULL, '1.20',
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('1e7e530ca0355eb1b7af83296f1d3397', '2026-09-17 15:08:24.151525+02', 'ONE-A1F0', 'measurement', 1700, 1.48, 6.3, 24.8, NULL, '1.20',
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('918990115d0bb9abbd2e88d00fdc8b62', '2026-09-17 15:08:35.215266+02', 'ONE-A1F0', 'measurement', 1800, 2.65, 6.31, 24, NULL, '1.20',
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('6c868fcaf01e4586ac2632d80425b849', '2026-09-17 15:08:43.626793+02', 'ONE-A1F0', 'measurement', 1500, 3.28, 6.21, 24, NULL, '1.20',
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00');

INSERT INTO corrections.journal_entries (
    entry_id, date_time, subject, type, ml, ec, ph, temp, notes, room,
    meta_extract_date_time, meta_source, meta_silver_date_time,
    meta_reviewed_by, meta_reviewed_date_time
) VALUES
('3afc3cd355ef371a172794a44c75df63', '2026-09-17 14:57:13.892601+02', 'ONE-A1F0', 'measurement', 1000, 1.37, 6.08, 21.9, NULL, NULL,
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('72dd6cca468995f46c6c1e6b03cc2c52', '2026-09-17 14:57:20.858315+02', 'ONE-A1F0', 'measurement', 1000, 1.3, 6.15, 22, NULL, NULL,
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('e7c1fcea03509d6dd3a60a6edbda45a9', '2026-09-17 14:57:34.845819+02', 'ONE-A1F0', 'measurement', 1400, 2.03, 6.29, 21.7, NULL, NULL,
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('07e6680619459c89877295ab1049227c', '2026-09-17 14:57:43.423173+02', 'ONE-A1F0', 'measurement', 1400, 1.71, 6.61, 21.5, NULL, NULL,
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('9f097350ea2069f12f56f1e0f590477f', '2026-09-17 15:08:12.795471+02', 'ONE-A1F0', 'measurement', 1700, 1.55, 6.38, 24.6, NULL, NULL,
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('1e7e530ca0355eb1b7af83296f1d3397', '2026-09-17 15:08:24.151525+02', 'ONE-A1F0', 'measurement', 1700, 1.48, 6.3, 24.8, NULL, NULL,
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('918990115d0bb9abbd2e88d00fdc8b62', '2026-09-17 15:08:35.215266+02', 'ONE-A1F0', 'measurement', 1800, 2.65, 6.31, 24, NULL, NULL,
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00'),
('6c868fcaf01e4586ac2632d80425b849', '2026-09-17 15:08:43.626793+02', 'ONE-A1F0', 'measurement', 1500, 3.28, 6.21, 24, NULL, NULL,
 '2026-10-05 12:57:33.060840+02', 'C:\Users\TeeltQ-Farms\OneDrive - Q-Farms\Bureaublad\DataWarehouse\SampleData\drip_drain_csv\journal-entries.csv',
 '2026-10-06 12:54:00+02', 'leone', '2026-10-06 13:45:00');

