# Reminders

Unfinished business. The user parks these deliberately: mention the relevant one when work gets near it, do not start it unprompted.

- **Test suite for the pipeline.** The checks of 2026-11-02 were run by hand. `.scratch/pipeline-test-suite/spec.md` needs its scenarios written again for load, test, undo.
- **The csv writer:** `src/bluelab_datastreamer/drip_drain.py` still writes the old 13 columns, so real daily files cannot load until the user updates it to `date_time, device, spot, ml, ec, ph, temperature, room`. Until then the samples are synthetic, in `SampleData/drip_drain_csv/synthetic/`. `drip_drain.py` also stays to change for a missing pen name (`None - Measurement`), which is refused.
- **Dry probes:** `ml, ec, ph, temperature` cannot be null for now, so a file with a dry probe is refused. The user will decide: an empty reading is null, never 0, because 0 is sometimes a valid reading. If `ec, ph, temperature` become nullable, the safe cast turns an uncastable value into null and no `not_null` catches it, so they need a data test that compares against the bronze text.
- **Mothers rooms:** 0.14 and 0.15 have lines `drip_1` to `drain_10`, which the spot data test and silver's check refuse. They are out for now.
- **Revisit once a proper extract is in place:** the row count data test tells loads apart by 30 seconds between `row_id`s, so two files closer together are judged as one. A load that dies between the insert and the undo leaves its rows in bronze (`_undo` in `src/datawarehouse/loaders/upload.py` says so and prints the delete): they reach silver with the next accepted upload, or block it if they are bad. Two uploads at once would judge each other's rows.
- **Source 2 and 3:** Excel, and a source that is not ours, reuse this shape later. Source 3 skips the undo and fixes in `stg_` with code. `git show db37e2a:DataWarehouseDbt/models/candidate/cand_journal_entries.sql` has the room carry-down, spot from row order and `ml` split from notes that `SampleData/drip_drain_csv/journal-entries.csv` needs. `aud_failures` has no original value for it: read bronze by `row_id`.
- **Prod is not migrated:** its bronze has the old columns and its corrections hold who reviewed what, which removing them drops, so that data needs a decision before the next release. Its images `v0.2.0-alpha` run the old code. `.env.prod` still points at the old sample csv. On a new database, run one whole `dbt build` before the first load.
- **Leftovers after a delete or rename:** dbt does not drop the relation of a deleted model or data test.
- **Duplicate keys inside one file** are not checked in `RecordSet`; the row tests report them.
- **Snapshots have no reader:** they are storage only. A deleted row's current version has `meta_is_deleted = 'True'`, as text, so a reader must filter it out.
- **Snapshot schema changes follow dbt's defaults:** a key moved to a new or renamed column splits the history at that build (old versions are marked deleted), and a column whose type changes (mainly in silver's yml) is not migrated and is fixed by hand when it happens. Dropping the database loses all history; on dev that is accepted.
- **Spot test is weak:** it checks each value, not that every room has each spot exactly once. Such a rule cannot be a constraint and stays a data test if added.
- **`is_working`** in `dim_devices` is informational: a device marked false still passes the relationship data test.
- **Range rules live in two files,** `stg_<dataset>.yml` and silver's checks. If they disagree the build fails with a database error, and the upload says it could not be checked.
- **Silver references dimensions in `dw_gold`,** against the layer order. Revisit when modeling gold.
- **Test results are append-only:** `test_result_rows` and `elementary_test_results` keep growing, which is fine at this volume.
- **Python gaps:** there is no test of `delete_from_bronze`, `read_failures` or `run_dbt_build` against a real database or dbt: they were checked by hand on 2026-11-02.
- **Python packages are not installed:** each image finds its package through `PYTHONPATH=/usr/app/src`, and its libraries are pinned in its Dockerfile. Revisit when two images share a package, or when the libraries should be declared once in `pyproject.toml` with a lock file: then `pip install .` in runtime and `pip install -e .` in dev.
- **Later layers:** gold and `experiments` are postponed, a prod target was removed on purpose and will come back later.
