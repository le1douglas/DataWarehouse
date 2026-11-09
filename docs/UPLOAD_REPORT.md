# Upload report

Adversarial testing of the upload: `meltano run tap-csv target-postgres` with a fresh `MELTANO_RUN_ID`, then
`dbt build --select source:dw_bronze.brnz_journal_entries+ --vars "{load_id: ...}"`. No code was changed.
Test files are `SampleData/drip_drain_csv/synthetic/fuzz-NN-*.csv`, each a copy of `valid-morning.csv` with the
change named below (line 2 = first data row) unless said otherwise.
Each test starts from the same bootstrapped database (DDL, then one whole `dbt build`) unless said otherwise.

Verdicts: **BUG** = wrong data reaches silver or the pipeline breaks; **SURPRISE** = works as coded but unlikely what
is wanted, or the message misleads; **OK** = behaves as documented.

Column **Valid files**: does it affect files shaped like `valid-morning.csv` / `valid-afternoon.csv` (header
`date_time,device,spot,ml,ec,ph,temperature,room`, comma, ISO time with microseconds and no zone, plain decimals,
40 rows):
**No** = needs characters or a shape that valid files never have; **Rare** = the valid format can hold it, but only
at certain times or with a wrong clock; **Yes, process** = the content is fine, it happens through how the load is
run (a resend, a rebuild, two builds at once, a crash, a setting).

---

## What still applies to valid files

**Rare, from the content:**
- Daylight saving (1.2, 1.3, 15.4): a reading between 02:00 and 02:59 on the last Sunday of October or March.
- Rounding to the second (8.2, 8.6, 8.7): every valid time has microseconds, so every row is rounded. It does harm
  only past midnight, for two readings under 1 s apart, or when two loads share a second.
- A wrong clock (1.7): any date in the valid format is accepted.

**Yes, from the process, with valid files (most were tested with them):**
- Two builds at the same time swap their loads (6.5, 6.6).
- Rebuilding an old `load_id` rolls silver back (4.2); a resent file overrides (4.1).
- Exit codes do not tell accepted from refused (7.2, 12.2); a crash blocks loads for 5 minutes (7.3).
- A seed change rebuilt with `seed_<name>+` inserts staging's last load into silver (9.3).
- A file cut at a line end, or a folder of files, is accepted (13.1, 14.1).
- New database (0.1), the audit gaps (8.8, 8.9, 12.1), retries (12.4).

Everything else (wrong date order, relative dates, odd numbers, header problems, delimiters, schema drift, swapped
columns) needs characters that valid files do not have.

---

## Findings, most serious first

About 75 scenarios. Numbers point to the log below.

**Wrong data reaches silver, with every test green**

1. **Day and month swapped** (1.1, 8.1): `03-11-2026` and `03/11/2026` become 11 March. The server's DateStyle is `ISO, MDY`, and the cast accepts any format Postgres can parse.
2. **Relative dates** (1.4): `yesterday 09:30:13` is accepted and resolved against the day of the *build*. The same bronze rows give a different date on another day.
3. **Daylight saving without a warning** (1.2, 1.3): an ambiguous 02:30 in October is silently taken as the second one, a nonexistent 02:30 in March is moved to 03:30. CLAUDE.md asks for a warning every time.
4. **Duplicate header name** (3.3): with two `ec` columns the last one wins, in bronze as well. The real value is gone everywhere.
5. **Another room's reading overwritten** (8.7): the key `(date_time, device)` has no room or spot in it. A clock glitch, or rounding to the second, replaces a different room's row with only an "earlier upload" warning.
6. **Concurrent builds swap their loads** (6.5, 6.6): staging is one shared view. When two builds overlap by about 1 s, the first build inserts the second load's rows and both report success: no override warning, and the first load's rows are missing from silver.
7. **Rebuilding an old `load_id` rolls silver back** (4.2): the last *build* wins, not the newest upload.

**The pipeline breaks or lies about its result**

8. **Bronze capped for good** (11.2, 11.3): a file with about 1585 extra columns is accepted. Dropping those columns afterwards does not help: Postgres still counts them toward its 1600-column limit, so any later file with a new column fails.
9. ~~**Foreign keys gone for good after a whole `dbt build`** (9.1)~~ **Fixed**: silver has no foreign keys any more, it runs the same relationship tests as staging and declares the dims with `depends_on`.
9b. **`dbt build --select seed_<name>+` inserts staging's last load into silver** (9.3), also a refused one. A seed change needs a whole `dbt build` without the var.
10. **Exit codes do not tell accepted from refused** (7.2, 12.2): meltano can fail after bronze has committed, and dbt can fail after silver has committed. A crashed build loses its override warnings for good.
11. **One crashed meltano run blocks every load for ~5 minutes** (7.3): it stays `RUNNING` in meltano's `runs` table.

**Surprises worth a decision**

- A new database needs a whole `dbt build` before its first load; CLAUDE.md says otherwise (0.1).
- Hex, octal, binary, underscore and exponent numbers are accepted (2.1–2.5).
- A file with a zone (`Z`, `+01:00`) is refused with "missing or not a date and time" (1.8, 1.9).
- 1970, `24:00`, second `60` and rounding past midnight are accepted (1.5–1.7, 8.6).
- `ec`/`ph` swapped by the writer passes (15.1); a file cut at a line end passes (13.1).
- A folder as `JOURNAL_ENTRIES_CSV` merges every csv in it into one load (14.1).
- Loads over 10 000 rows are not atomic (7.1).
- Semicolons, a wrong case or punctuation in the header add permanent bronze columns and give hundreds of "missing" messages (3.4, 3.5, 5.1).
- `aud_failures` cannot say which file a refusal belongs to (8.8). It misses database errors (8.9) and builds killed before the end hook (12.1), and it reports false duplicates when `date_time` is null (3.5).

---

## Log

### 0. Setup

| # | Scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 0.1 | New database: DDL, then the first load and its build, as CLAUDE.md says | Meltano loads 40 rows. The build ERRORs on both relationship tests: `dim_devices`, `dim_rooms` (and the seeds and Elementary's tables) do not exist, because `source:dw_bronze.brnz_journal_entries+` selects only what is downstream of bronze, and the dims are upstream of silver. A database error, not a test failure, so nothing reaches `aud_failures` (whose own tables do not exist either). Silver skipped | **SURPRISE** — CLAUDE.md "A new database needs the DDL, then the first load and its build" is not enough. The install guide's whole `dbt build` first is what works | Yes, process (a new database) |
| 0.2 | Whole `dbt build` without the var on that new database | Fails only the row-count test (compile error: `Required var 'load_id'`), builds seeds, dims, Elementary, `aud_failures`. This bootstrapped state is the start of every test below | OK (as the install guide says) | Yes, process |
| 0.3 | `valid-morning.csv` | 40 rows to silver, `load_id` in bronze equals `MELTANO_RUN_ID` | OK | Yes — this is the valid file |
| 0.4 | A `JOURNAL_ENTRIES_CSV` that does not exist | Meltano exits 1 with a Python traceback `File path does not exist`; the build of that `load_id` refuses on the row count (0 rows) | OK | Yes, process (a wrong path) |

### 1. Date and time (DateStyle of the server is `ISO, MDY`)

| # | File | `date_time` in line 2 | Result | Verdict | Valid files |
|---|---|---|---|---|---|
| 1.1 | fuzz-01-dmy-slash | `03/11/2026 09:30:13` (3 November, Dutch order) | **Accepted** as `2026-03-11 09:30:13+01`: Postgres reads slashes month first | **BUG** — silently the wrong date, eight months off. Any day ≤ 12 is swapped; day 13+ would be refused | No — valid files write `2026-11-03` |
| 1.2 | fuzz-02-dst-ambiguous | `2026-10-25T02:30:00` (happens twice that night) | **Accepted** as `02:30:00+01`, the second occurrence, no warning | **BUG** against CLAUDE.md: "warn every time this assumption is not true" | Rare — the valid format can hold it, only for a reading 02:00–02:59 on the last Sunday of October |
| 1.3 | fuzz-03-dst-gap | `2026-03-29T02:30:00` (does not exist) | **Accepted** and moved to `03:30:00+02`, no warning | **BUG**, same rule. The stored time is not the one in the file | Rare — as 1.2, last Sunday of March |
| 1.4 | fuzz-04-relative-word | `yesterday 09:30:13` | **Accepted** as `2026-11-04 09:30:13+01`: the day before the *build*. The regex only checks the end of the value | **BUG** — the same bronze rows give another date when built on another day. `today`, `tomorrow`, `now`-like words work the same | No |
| 1.5 | fuzz-05-hour-24 | `2026-11-03T24:00:00` | Accepted as `2026-11-04 00:00:00+01` | SURPRISE — valid ISO, but the row moves to the next day | No |
| 1.6 | fuzz-06-second-60 | `2026-11-03T09:30:60` | Accepted as `09:31:00` | SURPRISE — a leap second rolls into the next minute and can collide with another row's key | No |
| 1.7 | fuzz-07-epoch-1970 | `1970-01-01T00:00:00` | Accepted | SURPRISE — no plausibility range on `date_time` (a reset clock, 1970 or 2000, passes) | Rare — valid format, wrong clock |
| 1.8 | fuzz-08-explicit-offset | `2026-11-03T09:30:13+01:00` | Refused, `date_time is missing or not a date and time` | SURPRISE — `castable` documents an offset as accepted, but staging always appends ` Europe/Amsterdam`, so a correct, unambiguous value is refused with a wrong message (known TODO in staging) | No |
| 1.9 | fuzz-09-zulu | `2026-11-03T08:30:13Z` | Refused, same message | SURPRISE, as 1.8 | No |
| 1.10 | fuzz-10-two-digit-year | `26-11-03 09:30:13` | Refused | OK | No |

### 2. Number formats (Postgres 16+ input syntax)

The csv is written by a program of ours, so staging says anything unusual is an upstream fault. These are not refused:

| # | File | Change | Result | Verdict | Valid files |
|---|---|---|---|---|---|
| 2.1 | fuzz-11-ml-hex | `ml` = `0x4B0` | Accepted, silver `1200` | SURPRISE — `pg_input_is_valid` accepts hexadecimal integers | No |
| 2.2 | fuzz-12-ml-underscore | `ml` = `1_200` | Accepted, `1200` | SURPRISE — digit separators accepted | No |
| 2.3 | fuzz-18-ml-octal-binary | `ml` = `0o2260`, next row `0b11001110010` | Accepted, `1200` and `1650` | SURPRISE | No |
| 2.4 | fuzz-17-ec-hex | `ec` = `0x2` | Accepted, `2` | SURPRISE — numeric too | No |
| 2.5 | fuzz-15-ec-exponent | `ec` = `164e-2` | Accepted, `1.64` | SURPRISE | No |
| 2.6 | fuzz-16-padded-numbers | `ml` = ` 1200 `, `temperature` = ` 22.8` | Accepted, spaces dropped. Bronze keeps them | SURPRISE — a space is kept for text columns (`device`, `room` fail the relationship), dropped for numbers: inconsistent | No |
| 2.7 | fuzz-13-ec-nan | `ec` = `NaN` | Refused by `accepted_range` (NaN sorts above every number) | OK, but only by luck of the upper bound: `NaN = round(NaN, 2)` is true and NaN passes `not_null` | No |
| 2.8 | fuzz-14-ec-infinity | `ec` = `Infinity` | Refused by `accepted_range` | OK | No |

### 3. Header tricks

| # | File | Change | Result | Verdict | Valid files |
|---|---|---|---|---|---|
| 3.1 | fuzz-19-own-row-id | extra column `row_id` with chosen uuids | Meltano fails: `Could not convert column ... row_id from 'UUID' to 'TEXT'`, nothing loaded, build refuses on the row count | OK by accident — a file cannot set its own key, but only because target-postgres would have to change the type. The message does not say why | No |
| 3.2 | fuzz-20-own-load-id | extra column `load_id` = a fixed uuid | The stream map wins: rows get the run's `load_id` | OK | No |
| 3.3 | fuzz-21-duplicate-ec-header | a second `ec` column at the end, `9.99` on every row | **Accepted**: `ec` is `9.99` in bronze and silver; the real `ec` of the first column is gone, even from bronze | **BUG** — silent wrong value, and bronze is no longer what arrived | No |
| 3.4 | fuzz-22-uppercase-header | `DATE_TIME,Device,SPOT,ML,...` | 8 new columns (`"DATE_TIME"`, `"Device"`, ...) are added to `brnz_journal_entries` for good; every lower-case column is null, refused with 8×40 `not_null` failures | SURPRISE — refused, but the message is "missing" 320 times, not "the header is wrong", and bronze gains 8 columns forever (the known schema drift, now from casing alone) | No |
| 3.5 | fuzz-23-punctuated-header | `Date Time` and `p-h` | Two new bronze columns; refused with `date_time` and `ph` not null **plus 40 × "this device already has a measurement at this moment"** | SURPRISE — with `date_time` null, the compound unique test groups the nulls together and reports 40 false duplicates. In 3.4 it did not, because `device` was null too | No |

### 4. More than one load

| # | Scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 4.1 | Load A = `valid-morning`, load B = fuzz-24-morning-resent-new-ec (same rows, `ec` = 5.55) | B replaces all 40 rows with WARN 40 | OK, as documented | Yes, process (a file sent again) |
| 4.2 | Then `dbt build` with A's `load_id` again | **A's old values are back in silver** (`ec` 1.21–3.41), WARN 40, the build reports success | **BUG** — REMINDERS says "the newest upload wins"; it is the last *build* that wins. Any re-run of an old build (retry, orchestrator replay, typo in the id) silently rolls silver back | Yes, process (an old id built again) |
| 4.3 | `dbt build` with A's id a third time | No warning, no change | OK — idempotent | Yes, process |
| 4.4 | Snapshot after 4.1–4.3 | 200 rows, 80 with `meta_valid_to` null: 40 live and 40 "deleted" markers of B. A's row_ids are live again after being marked deleted | OK, consistent with REMINDERS, but history now says a deleted row came back to life | Yes, process |
| 4.5 | Two meltano runs with the same `MELTANO_RUN_ID` (`valid-afternoon` twice) | Both succeed; 80 rows share one `load_id`; the build refuses on the row count | OK — but nothing stops reusing an id, and a 20-row file sent twice would make one accepted 40-row load whose second half all fails `unique_within_upload` | Yes, process (a run id reused) |

### 5. File structure

| # | File | Change | Result | Verdict | Valid files |
|---|---|---|---|---|---|
| 5.1 | fuzz-25-semicolon | `;` as delimiter (the Dutch Excel default) | Meltano succeeds: one column `"date_time;device;spot;ml;ec;ph;temperature;room"` is added to bronze for good; refused with 8 × 40 `not_null` | SURPRISE — the likeliest real-world mistake gets 320 "missing" messages and a permanent junk column | No |
| 5.2 | fuzz-26-nul-byte | NUL byte inside `spot` | target-postgres fails (`text fields cannot contain NUL`), nothing loaded, no leftover table in `dw_bronze` (it is a real temp table) | OK — atomic, message is a traceback | No |
| 5.3 | fuzz-27-cr-only | old-Mac `\r` line endings | Accepted, 40 rows | OK | No |
| 5.4 | fuzz-28-huge-field | a 200 000 character `room` (quoted) | tap-csv fails (Python's csv field limit is 131 072), nothing loaded | OK | No |
| 5.5 | fuzz-29-concatenated-header | two exports joined, header repeated in the middle | 41 rows, refused only by the row count | OK, but by luck: two 10-row files joined (21 rows) would reach staging and fail on the header row's values instead | No — needs two files joined |
| 5.6 | fuzz-30-blank-space-line | a line of 3 spaces in the middle | Becomes a row (`date_time` = `'   '`), 41 rows, refused by the row count | OK — a blank line is skipped, a line of spaces is not | No |

### 6. Process faults

| # | Scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 6.1 | `MELTANO_RUN_ID` not set | Meltano makes its own run id, but the stream map reads the env var: `NotNullViolation` on `load_id`, nothing loaded | OK (as the DDL comment says), message is a traceback | Yes, process (env var) |
| 6.2 | `MELTANO_RUN_ID` empty | Same as 6.1 | OK | Yes, process (env var) |
| 6.3 | `MELTANO_RUN_ID=load-2026-11-05` | Meltano refuses before running: `not a valid UUID` | OK | Yes, process (env var) |
| 6.4 | Upper-case uuid | Stored lower case, the upper-case var still matches | OK | Yes, process (env var) |
| 6.5 | **Two builds at the same time**, empty silver: A = `valid-morning`, B = `valid-afternoon`, B started 1–1.5 s after A | **A reports success (PASS=27) but silver holds B's 40 rows and none of A's. B reports a database error (`relation "slvr_journal_entries" already exists`), yet its rows are the ones in silver.** With 0.5 s or 2 s the result happened to be right | **BUG** — staging is one shared view whose `load_id` filter is fixed at build time; the second build replaces it while the first is between its tests and silver. Both verdicts are wrong | **Yes, process** — tested with the two valid files |
| 6.6 | Same, silver already exists (C accepted first), A = `valid-morning`, B = morning resent with `ec` 5.55, B 1–1.5 s later | **Both builds green, zero override warnings; silver has B's 40 rows, A's rows were never inserted.** Started serially, B would have warned 40 overrides | **BUG** — an accepted load is missing from silver, and the override it caused is not reported. An orchestrator running two datasets or two files in parallel hits this. (Both builds also write the same `target/` folder) | **Yes, process** — tested with valid files |
| 6.7 | Same race, B fails the row count | B stops before staging, no effect on A | OK — only loads that pass the source test can swap the view | Yes, process |

### 7. Killed and failed loads

| # | Scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 7.1 | fuzz-32-big-300k (300 000 rows), meltano container killed after 5 s (file deleted after the test, 20 MB) | **10 000 rows stay in bronze** under that `load_id`: target-postgres commits every 10 000 records | SURPRISE — a load is atomic only up to 10 000 rows. Harmless today (the row count refuses it) but the "a load is all or nothing" assumption does not hold for big files, and a refused 300k file stays in bronze forever | No — needs more than 10 000 rows; a valid file has 40 |
| 7.2 | meltano's `state` table locked, meltano killed after bronze committed | **Meltano exits 137 (failed) but all 40 rows are in bronze** | **BUG** for an orchestrator: "meltano failed" does not mean "nothing loaded". A retry with a new id loads the file twice (40 override warnings), skipping the build leaves a load that is never judged | **Yes, process** — tested with a valid file |
| 7.3 | The next load right after 7.2 | **Refused for ~5 minutes**: `Another 'dw:tap-csv-to-target-postgres' pipeline is already running ... Wait until ...` — the killed run is still `RUNNING` in meltano's `runs` table | SURPRISE — every crash blocks all loads until meltano's heartbeat expires (or `--force`) | **Yes, process** |
| 7.4 | Two meltano loads started 1 s apart | The second fails with the same "already running" message; only the first loads | OK — meltano serialises loads. The builds are not serialised (6.5, 6.6) | Yes, process |

### 8. Rounding, overrides and the audit

| # | File / scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 8.1 | fuzz-33-dmy-dashes: `03-11-2026 09:30:13` | **Accepted as 11 March**, like 1.1 | **BUG** — the dash form is what a Dutch-locale Excel writes | No |
| 8.2 | fuzz-34-subsecond-collision: line 2 `09:30:13.4`, line 3 `09:30:12.6` (different spots) | Refused: both round to `09:30:13`, "this device already has a measurement at this moment" ×2 | SURPRISE — two real measurements 0.8 s apart are called duplicates; the message hides that the cause is rounding | Rare — every valid time has microseconds and is rounded; a collision needs two readings less than 1 s apart, valid files have about 15 s |
| 8.3 | fuzz-35-leading-space-time: ` 2026-11-03T09:30:13` | Accepted | OK | No |
| 8.4 | fuzz-36-trailing-space-time: `2026-11-03T09:30:13 ` | Refused: two spaces before the appended zone do not match the regex | SURPRISE — leading space fine, trailing space refused, same message as a missing date | No |
| 8.5 | fuzz-37-time-only: `09:30:13` | Refused | OK | No |
| 8.6 | fuzz-38-midnight-rollover: `2026-11-03T23:59:59.7` | Accepted as `2026-11-04 00:00:00` | SURPRISE — rounding moves a row to the next day (a daily report counts it on the wrong day) | Rare — microseconds: a reading in the last half second before midnight |
| 8.7 | A = `valid-morning`, then B = fuzz-39-afternoon-clock-collides: `valid-afternoon` with line 2 at `09:30:13.9` (room 1.23), which rounds onto A's line 2 (room 1.30) | Accepted with WARN 1. **Room 1.30 now has 3 readings, its `drip_left` is gone, replaced by room 1.23's.** Silver 79 rows | **BUG** — the key `(date_time, device)` ignores room and spot, so a clock glitch overwrites another room's measurement; the warning text "replaces the one of an earlier upload" suggests a resend, not a different room | Rare — the rounding hits every valid row; another room is overwritten only when two loads share a second (clock glitch) |
| 8.8 | `aud_failures` after a row-count refusal | One row: `row_id` null, no `load_id`, no file name | SURPRISE — the user cannot tell which file was refused, except by the time of the run | Yes, process (any refused load) |
| 8.9 | `aud_failures` after a database error (0.1, 6.5) | Nothing: it keeps `status = 'fail'` only | SURPRISE — a load refused by an error leaves no trace there | Yes, process |

### 9. Dimensions

| # | Scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 9.1 | Accept a load, then a whole `dbt build` (with the var), then another load | Silver's foreign keys to `dim_devices` and `dim_rooms` exist after the first load; **after the whole build both are gone and never come back** (constraints `cccccffnnnnnnnnnpu` → `cccccnnnnnnnnnpu`) | **BUG** — rebuilding a dim table drops it with `CASCADE`, and an incremental silver only gets its constraints when it is created, which `full_refresh=false` prevents. The dims' yml says the key "is lost until the next successful build": it is lost for good. Silver keeps rows of a room removed from the seed. **Fixed**: the foreign keys are replaced by relationship tests on silver, and `-- depends_on:` the dims in `slvr_journal_entries.sql` keeps a failed staging relationship test skipping silver (without it, an unknown device reached silver: retested, now skipped) | **Yes, process** (a whole `dbt build`) |
| 9.2 | (from reading) a room added to `seed_rooms.csv` | The load build (`source:...+`) never reloads seeds or dims; only a whole build does | SURPRISE | Yes, process (a seed change) |
| 9.3 | `dbt build --select seed_devices+ seed_rooms+` after a seed change | Rebuilds seeds and dims, runs only the relationship tests of staging, then rebuilds silver from staging (`INSERT 0 40`): whatever load staging last held is inserted, without its other data tests | **BUG** — if the last built load was refused (for example on the row count), it reaches silver. Use a whole `dbt build` without the var, which fails on staging and skips silver (CODING_STANDARDS.md, Seeds) | Yes, process (a seed change) |

### 10. Header shapes from spreadsheet tools

| # | File | Change | Result | Verdict | Valid files |
|---|---|---|---|---|---|
| 10.1 | fuzz-40-trailing-comma | a `,` at the end of every line (common in Excel exports) | Meltano fails: `zero-length delimited identifier at or near """"` (target-postgres tries to add a column with an empty name), nothing loaded | OK — refused, but the message is an SQL syntax error | No |
| 10.2 | fuzz-41-empty-header-name | the `ec` header left empty | Same as 10.1 | OK, same message | No |

### 11. Schema drift taken to the limit

| # | File / scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 11.1 | fuzz-42-1700-extra-columns: 1700 empty extra columns | Meltano fails `TooManyColumns: tables can have at most 1600 columns`; rolled back, bronze keeps 10 columns | OK | No |
| 11.2 | fuzz-43-1585-extra-columns: 1585 empty extra columns | **Accepted** (extra columns are ignored by staging); **bronze now has 1595 columns** | SURPRISE — an extra column is not refused (known), here at scale | No |
| 11.3 | After 11.2, the 1585 columns are dropped by hand: bronze shows 10 columns again. Then fuzz-44-20-extra-columns (20 extra) | **`TooManyColumns`**: Postgres counts dropped columns toward the 1600 limit. From now on any file with any new column fails; files with the 8 known columns still work (valid-afternoon accepted) | **BUG** — one bad file permanently caps bronze; the only fix is recreating the append-only table. The role without `ALTER` from REMINDERS would prevent it | No — only after 11.2 has happened; valid files still load then |

### 12. Crashes during the build

| # | Scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 12.1 | fuzz-25-semicolon (320 failures), dbt container killed after its tests ran, before Elementary's `on-run-end` hook | **Nothing in `aud_failures`, `elementary_test_results` or `test_result_rows`** for that build: Elementary uploads results only at the end of the run. Building the same id again records the 320 rows | SURPRISE — a refused load can leave no trace; whoever retries must know to rebuild it | Yes, process (a crash) |
| 12.2 | Postgres restarted right as silver started (load = morning resent, `ec` 5.55, over an accepted morning) | Silver committed (`INSERT 0 40`); then the snapshot ERRORs and the end hook does not run. **The build is red, but the load is accepted** (silver `ec` = 5.55). Its 40 override warnings are never stored. The snapshot catches up on the next build, with a later `meta_valid_from` | **BUG** for an orchestrator — "build failed" does not mean "refused"; the overrides of that load are lost from the audit for good | **Yes, process** — tested with a valid-format file |
| 12.3 | `--vars "{load_id: }"` (empty) | Compiles to `load_id = 'None'::uuid`: a database error on the row-count test, not the planned compile error | OK — still refused, but no record in `aud_failures` (8.9) | Yes, process (operator) |
| 12.4 | The same `load_id` built twice at the same moment (a retry overlapping the first try), silver present | At 0 s: one build fails at random with `relation "stg_journal_entries__dbt_backup" already exists`. At 0.5 s: both green, silver right, **the 40 override warnings stored twice (80)** | SURPRISE | Yes, process (a retry) |

### 13. Truncated files (writer still writing, partial sync)

| # | File | Result | Verdict | Valid files |
|---|---|---|---|---|
| 13.1 | fuzz-45-truncated-at-line: the last 3 rows cut off at a line end | **Accepted, 37 rows**; room 0.33 has 1 of its 4 spots | SURPRISE — nothing checks that a file is complete (row count 20–40 and the per-value spot test let it through; REMINDERS "spot test is weak") | **Yes, process** — a valid file cut at a line end still looks valid |
| 13.2 | fuzz-46-truncated-mid-line: cut after `...,ONE` | Refused: the short last row is nulls | OK | Yes, process |
| 13.3 | fuzz-47-truncated-in-last-field: cut before `room` | Refused: `room` missing | OK | Yes, process |

### 14. What `JOURNAL_ENTRIES_CSV` points at

| # | Scenario | Result | Verdict | Valid files |
|---|---|---|---|---|
| 14.1 | `JOURNAL_ENTRIES_CSV=drip_drain_csv/synthetic/fuzz-48-folder`: a **folder** with two 20-row csv files and a `.txt` | tap-csv reads every `.csv` in the folder as one stream: **accepted as one 40-row load**, the `.txt` ignored | SURPRISE — pointing the env var at the datastreamer's daily folder would merge every part of the day into one load, and reload all of them (40 override warnings) on every run | **Yes, process** — a folder of valid files |

### 15. Last content checks (the results matched the prediction, the sign to stop)

| # | File | Change | Result | Verdict | Valid files |
|---|---|---|---|---|---|
| 15.1 | fuzz-49-ec-ph-swapped | `ec` and `ph` values swapped on every row, header unchanged | **Accepted**: every `ec` 5.2–6.8 and `ph` 1.2–3.4 fall inside each other's range | SURPRISE — a writer bug that swaps two columns passes; the ranges (ec 0–10, ph 0–14) overlap too much to catch it | No — needs a writer bug |
| 15.2 | fuzz-50-single-digit-hour | `2026-11-03 9:30:13` | Refused (the regex wants two hour digits) | OK — but it is a valid time, refused as "missing" | No |
| 15.3 | fuzz-51-feb-29 | `2026-02-29T09:30:13` | Refused | OK | No |
| 15.4 | fuzz-52-dst-two-real-0230 | Two rows at `2026-10-25T02:30:00`, meant as the two real 02:30s of that night | Refused as duplicates | OK given 1.2: without a zone they cannot be told apart | Rare — as 1.2 |

---

## Not tested

- A OneDrive "online-only" placeholder file read through the bind mount (could not be made on purpose).
- The prod stack: not touched.
- Data tests that disagree with silver's constraints: none found. Every staging test except the row count and, since the fix of 9.1, the relationship tests has a matching constraint. The race in 6.5/6.6 mixes accepted loads; an unknown device or room it lets in would be reported by silver's relationship tests, not stopped (not retested).
