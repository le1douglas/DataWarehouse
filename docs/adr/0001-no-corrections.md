# No corrections: bad data is fixed where it came from

The warehouse used to let a reviewer correct flagged rows in a web app, kept apart from bronze and applied on every build. That is gone: a file that fails a data test is refused and fixed upstream, and every table, snapshot and page of the corrections loop was removed on 2026-11-02. A fix inside the warehouse hid the fault from the program that caused it and made the published data depend on a second, hand-kept input. Refusing the whole file for one bad row is deliberate: silver keeps its last good version until the source is right.

The price is that a person can no longer fix a value without the source, and the record of who reviewed what is lost. A source we do not control will not send a file again, so it cannot be refused: it always loads, and is fixed by code in staging.

dbt can only test data already in the database, so load, test, undo is how a file is refused: it is inserted, judged, and deleted again. Load metadata and meta tables went too, on the expectation that an extract tool such as Airbyte or Fivetran brings its own.
