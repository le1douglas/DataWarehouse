# Time zone report

Every place that sets, reads or depends on a time zone, as of 2026-10-22 on the branch `docs-update`, after the dev
images were rebuilt and the dev containers recreated from the new compose (see [Tested after the
rebuild](#tested-after-the-rebuild)). The zone is
written once, in `docker/compose.yaml` (`x-timezone: &timezone Europe/Amsterdam`), and reaches the postgres, dbt,
loader and datastreamer services as `TZ`. No code hardcodes `Europe/Amsterdam` any more: it appears only in
comments and docs.

Everything below was checked, not assumed: in the running containers, in throwaway containers, on a copy of the dbt
project, in the installed sources of dbt and the postgres image, and with read-only queries on dev and prod.

## Needs attention

- **Fix the corrections workbook: its date-times have no zone.** Nothing wrong gets through, the warehouse refuses
  them, but until the workbook is fixed no correction reaches silver:
  - `date_time` (`2026-09-17 15:13:08` today) must have a zone: `... Europe/Amsterdam`, or an offset. Without one, the
    castable test flags the correction and silver is not built.
  - `meta_reviewed_date_time` (`2026-10-18 14:30:00` today) must be written with its offset
    (`2026-10-18T14:30:00+02:00`), for example with Power Query's
    `DateTimeZone.ToText(DateTimeZone.LocalNow(), "yyyy-MM-ddTHH:mm:sszzz")`. Without one,
    `ck_meta_corrections_description` refuses the whole corrections load.
- **Assumption: corrections are made in the same time zone as the original file.** Candidate sorts `date_time` as
  text, which is time order only while the rows are on the same clock. Not protected: a correction written on another
  clock than its source rows (`...T13:13:08Z` among `...T15:13:08 Europe/Amsterdam`) is a valid time, so nothing
  flags it, but it sorts two hours off and can land in the wrong room group or position. Today every source row is
  on the Amsterdam clock. A fix that removes the assumption was drafted and postponed on 2026-10-22: candidate sorts
  on `date_time_order`, the time converted to the Amsterdam clock when it can be read and the text when it cannot,
  only for the ordering.
- **Daylight saving times are changed without a warning.** Ignored for now (decided on 2026-10-22). A source time
  without a zone, in the spring gap (`2026-03-29T02:30:00 Europe/Amsterdam`), becomes `03:30:00+02`. One in the
  repeated autumn hour (`2026-10-25T02:30:00 Europe/Amsterdam`) is ambiguous and is taken as the second one (`+01`).
  Bronze has no row in those hours today.
- **Docs and comments out of date:**
  - `Database/dumps/refresh_dev_from_prod.ps1` line 28: "the postgres container's clock is in UTC" is no longer true:
    both postgres containers have `TZ` since 2026-10-22.
  - `docs/DOCKER_IMPLEMENTATION.md` lines 204-205 and 316-317 put `TZ=Europe/Amsterdam` in `.env.transformer` and
    `.env.loader`; `docker/create_env_files.ps1` no longer writes it, compose sets it.
  - `docs/DOCKER_PLAN.md` line 29 says the same ("in the service's env file").

## Pending: done at the next recreate or release

Nothing to do but recreate a container or make the next release, which happen anyway. Remove each item once it is
done.

- **The Dev Containers were removed.** "Reopen in Container" creates them again from the new compose.
- **Prod is empty until the next release.** Prod's database was rebuilt from scratch on 2026-10-22 with the new DDL
  and has no data. Its images `v0.1.2-alpha` are older than these changes, so nothing is loaded or built in prod
  before the next release:
  - `loader:v0.1.2-alpha` writes `meta_extract_date_time` without an offset, which `ck_meta_bronze_description`
    refuses: a bronze load fails.
  - `dbt:v0.1.2-alpha` does not have `macros/snapshot_get_time.sql`, so a build would create the snapshot tables
    without a zone (dbt sets their column types only when it creates them), and it does not have the new staging,
    castable and silver. Also in `docs/REMINDERS.md`.

## Works implicitly

These never name a zone: they take the session's or the machine's, which is Amsterdam today.

- **Every database session** gets the server's zone. No client sets its own: dbt-postgres passes only `search_path`
  in its connection options, psycopg sends nothing, and the Excel ODBC DSN `PostgreSQL35W` has no connection
  settings.
- **`Database/debug_row.sql`**: `uuid_extract_timestamp(row_id)::TEXT` and every `::TEXT` of a `timestamptz` show
  the session's zone.
- **`row_id`** is a uuidv7 from the server's clock in UTC milliseconds: it holds no zone and needs none.
- **Windows** (`W. Europe Standard Time`, the same rules as Amsterdam): the timestamps of `onepen_bridge.py` (in its
  messages only, not in the data) and the name of the dump in `refresh_dev_from_prod.ps1`.
- **The source export's `date_time`** has no zone; it is assumed to be Amsterdam, the phone's local time, and staging
  writes it (see dbt below).
- **dbt's own times are always UTC**, whatever `TZ` says: its log lines (`dbt_common/events/helpers.py` and
  `logger.py`) and `run_started_at` (`dbt/tracking.py`). The project uses neither.

## Works explicitly, fails when TZ is not set

These read `TZ` from compose and stop when it is unset, empty or misspelled, instead of guessing.

- **postgres**: `command` in `compose.yaml` runs `postgres -c timezone="$TZ" -c log_timezone="$TZ"` through `sh`
  (`$$` keeps compose from replacing it). The image's entrypoint sees `sh` as the command and runs it as is, and `sh`
  then runs `docker-entrypoint.sh postgres ...` the normal way. With `TZ` unset, empty or misspelled, postgres refuses
  to start: `FATAL: invalid value for parameter "TimeZone"`. On a new volume, initdb also writes the zone of `TZ` into
  `postgresql.conf`, as it did when both volumes were rebuilt on 2026-10-22.
- **dbt**: `dbt_project.yml` sets the var `timezone` to `env_var('TZ')`. Every datetime is text up to silver, with
  its time zone written from staging on:
  - `stg_journal_entries.sql`: when the source text ends right after the time (`2026-09-17T15:13:08.363212`), staging
    appends the var (`... Europe/Amsterdam`). Anything else is left as the source wrote it, `T` and decimals included.
  - `aud_castable.sql`: a `timestamptz` column must be readable as `timestamptz(0)` and end in a zone that cannot be
    misread: `Z`, an offset (`+02`, `+0200`, `+02:00`), `UTC`, or a name with a slash (`Europe/Amsterdam`). A missing
    zone, an abbreviation (`CST`, `CEST`), a bare date or `now` are flagged like any other castable error.
  - `silver.sql`: `date_time` is cast with `::timestamptz(0)` like any other column, rounded to the second. Silver no
    longer assigns a zone, so the result does not depend on the session's zone.
  - `TZ` unset: dbt stops at parse, `Env var required but not provided: 'TZ'`.
  - `TZ` empty or misspelled: staging appends `''` or the wrong name, and the castable test flags every row, so silver
    is not built.
  - `--vars '{timezone: ...}'` on the command line still overrides it.
  - `RUN dbt deps` in `docker/dbt/Dockerfile` has no `TZ` at build time and works: `dbt deps` does not read the var.
- **meta tables**: `ck_meta_bronze_description` and `ck_meta_corrections_description` in the DDL refuse a kind ending
  in `_date_time` whose description is not a real date-time with its offset (`2026-10-22T14:42:08+02:00`). Metadata
  never reaches candidate, so it is checked at the load instead of by a castable test. Tested on 2026-10-22: no zone
  (`2026-10-18 14:30:00`), a zone name (`... Europe/Amsterdam`) and an impossible hour (`T25:30:00+02:00`) are
  refused, an offset is accepted, and other kinds (`meta_source`) are not checked.
- **loader**: `src/datawarehouse/config.py` sets `TIMEZONE = ZoneInfo(os.environ["TZ"])`, and `__main__.py` passes it
  to `CSVReader.read`, which stamps `meta_extract_date_time` with `datetime.now(timezone)`, written with its offset
  (`2026-10-22T15:56:21+02:00`), exact even in the repeated autumn hour.
- **datastreamer**: `src/bluelab_datastreamer/drip_drain.py` sets the same `TIMEZONE`. Its `now()` stamps each reading
  (moved there from `onepen.py`), and `daily_csv` dates the csv name with it.
- Both read the zone themselves instead of taking the container's clock, which falls back to UTC without an error
  when `TZ` is unset, empty or misspelled. Tested on 2026-10-22, both stop at start:
  - `TZ` unset: `KeyError: 'TZ'`.
  - `TZ` empty: `ValueError: ZoneInfo keys must be normalized relative paths`.
  - `TZ` misspelled: `ZoneInfoNotFoundError: 'No time zone found with key Europe/Amsterdm'`.
  - `TZ=Europe/Amsterdam`: `meta_extract_date_time` `2026-10-22 14:42:08`, a reading `2026-10-22T14:42:12.902500`,
    daily csv `261022-2.csv`, all in Amsterdam time.

## Tested after the rebuild

On 2026-10-22 the images `dbt:dev`, `loader:dev` and `datastreamer:dev` were rebuilt, and `dw-dev-postgres-1` was
recreated with `up -d --force-recreate --no-deps postgres`. The other services were tested in new containers
(`run --rm`) from the same compose files, before and after the change to the time zone of `date_time`.

| Service | Result |
|---|---|
| postgres | `TZ=Europe/Amsterdam`, clock and log lines in CEST. `TimeZone` and `log_timezone` are `Europe/Amsterdam` from the command line. Process 1 is `postgres -c timezone=Europe/Amsterdam -c log_timezone=Europe/Amsterdam` as the user postgres, so the `sh` wrapper hands over to the entrypoint as intended. The 104 bronze rows are still there. |
| loader | `TZ=Europe/Amsterdam`, clock in CEST, `datetime.now()` in Amsterdam time. |
| datastreamer | `TZ=Europe/Amsterdam`, clock in CEST, a reading's `date_time` in Amsterdam time (`2026-10-22T14:27:58.807949`), daily csv `261022-1.csv`. |
| dbt | `TZ=Europe/Amsterdam`, clock in CEST. Staging appends ` Europe/Amsterdam` to all 104 rows. `dbt build` has the same result as before the change (castable 1, position 8, silver skipped). Silver's cast, run by hand on the 103 rows that pass, gives the same instants in a UTC and a New York session (`2026-09-17T15:13:08.363212 Europe/Amsterdam` is `13:13:08+00`). |
| corrections (dev) | In a transaction rolled back after: a correction `...T15:13:08 Europe/Amsterdam` passes castable, `2026-09-17 15:13:08` and `...T15:13:08 CST` are flagged on `date_time`. |
| rebuild (dev and prod) | Both databases rebuilt from an empty volume with the new DDL: `postgresql.conf` now has `timezone` and `log_timezone` `Europe/Amsterdam` from `TZ`, both meta tables have their `ck_..._description`, `date_time` is `VARCHAR(100)`. Dev reloaded: 104 rows, every `meta_extract_date_time` `2026-10-22T16:04:56+02:00` and within 2 seconds of its row's uuidv7 time, `dbt build` as before (castable 1, position 8, silver skipped), snapshot times `timestamp with time zone`. Prod left empty. |
| `date_time` length (dev and prod) | `VARCHAR(100)` in bronze and corrections and `max_length=100` in the Python models: the longest zone name is 30 characters (`America/North_Dakota/New_Salem`), so the longest `date_time` is 57. The staging and candidate views were saved, dropped and created again around the change, unchanged. |
| snapshots (dev) | Dropped and built again with `macros/snapshot_get_time.sql`: `meta_valid_from`, `meta_valid_to` and `meta_updated_at` of `snap_corr_journal_entries` and `snap_meta_corrections` are `timestamp with time zone`. They are empty, so no snapshot time was written yet. `snap_slvr_journal_entries` does not exist yet, because the data tests fail and silver is skipped. |

## Checked and fine

- Every image has tzdata (2026c); postgres is built with `--with-system-tzdata=/usr/share/zoneinfo`.
- Snapshot times hold their zone (dev): `now()` is a `timestamptz`, an instant, whatever the session's zone.
- The loader's stamps are right: every `meta_extract_date_time` of the dev load, `2026-10-22T16:04:56+02:00`, is
  within 2 seconds of its row's uuidv7 time.
- `debug_row.sql` shows the bronze load time as `uuid_extract_timestamp(row_id)::TEXT`, a `timestamptz` with its
  offset (`2026-10-22 11:00:52.551+02`).
- The comment "dbt itself always logs in UTC" in `compose.yaml` is true.
