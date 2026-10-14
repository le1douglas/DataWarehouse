# Silver is generated from its yml, and every column is cast

The columns and types of silver are declared once, in `models/silver/slvr_<dataset>.yml`, with an enforced dbt contract. Silver is not written by hand: the `silver_select` macro selects `row_id` unchanged and casts every other column of the yml from candidate's text to its `data_type`. The `castable` macro is the body of `aud_<dataset>__castable` and checks the same columns with `pg_input_is_valid`. There is one rule by type and none by column: a `timestamptz` column is given the `timezone` var before the cast, and is checked as a `timestamp`, because its text has no zone yet. We chose this because the types were a var with a list of names and `numeric` hardcoded in silver and in the test, so changing a type meant editing SQL in two places, nothing checked the types silver really had, and silver's columns were not documented.

To make that possible, candidate's column names are silver's. The room as recorded, which is the correctable one, is called `room_raw` from staging onwards (in staging, corrections, `CorrRecordJournalEntries` and the Excel `corrected` sheet), and candidate's derived room is called `room`, which used to be `room_filled`.

This reopens part of ADR-0003: its rejected design also read column types from a yml. What ADR-0003 rejected was the guarded cast in staging and the machinery around it, not the yml. The casts stay after the corrections and are unguarded, as ADR-0003 decided.

## Considered Options

- **The var as a map** (`column: type` in `dbt_project.yml`). Smallest change, but no contract and no column documentation.
- **A generic `castable` test per column** in candidate's yml, with the type as its argument. Silver would have had to read the types out of the test arguments, every column would have had its own failure table and rule name, and `dbt docs` would not show silver's types.
- **Cast only the flagged columns** (`meta: {cast_from_text: true}`). This adds a flag per column that can contradict `data_type`, and silver stays hand-written.

## Consequences

- To change a type, edit the yml. Silver, the castable test and the contract follow, and `dbt docs generate` shows silver's columns with their types and descriptions.
- A new dataset is one yml and two one-line files: `slvr_<dataset>.sql` and `aud_<dataset>__castable.sql`.
- Silver cannot hold logic for one dataset. A derived value belongs in candidate, under the name it has in silver.
- A candidate column that is not in the yml (`room_index`, `position_index`, `meta_is_corrected`) is not published.
- The castable test also checks `text` columns, which always pass.
- `date_time` is text up to silver like every other column, which replaces ADR-0003's "`date_time` is still cast in staging". Staging gives it the shape `YYYY-MM-DD HH:MM:SS` with text rules, and a correction in any other shape is refused by `CorrRecordJournalEntries` and by a check constraint on the table. Candidate sorts room groups by the text, which is the time order only because the shape is fixed. A guarded cast in candidate (`sort_date_time`) was rejected: the shape belongs to the input, so the rest of the code can assume it. A `date_time` in the shape that is not a timestamp is a flagged row, not a failed build.
- dbt warns that `numeric` has no precision. Postgres does not round an unconstrained `numeric`, so the warning is accepted.
