# Corrections are applied before the cast, and silver casts

Staging and corrections keep the measurements as text. Candidate applies the corrections to that text and derives room groups and positions, and silver casts the measurements to `numeric`. The data test `aud_journal_entries__castable` checks every value with `pg_input_is_valid` on candidate, so a value that cannot be cast is a flagged row and silver is skipped. We chose this so that any value, received or corrected, can be fixed by a correction: a cast before the corrections would fail the build on a bad value before a correction could replace it. The reviewer still sees silver's rows and columns in candidate; only the types are missing, which Excel does not show.

The dbt layers lost their meta tables with this change. `meta_staging`, `meta_candidate` and `meta_silver` only stamped the first build that saw a row, and the cast errors no longer need a place of their own: the castable failure table lists them.

## Considered Options

- **Guarded casts in staging** (a value that cannot be cast becomes null and is reported in `meta_staging__failed_casts`). The previous design. It worked, but needed two macros that read the column types from a yml, a view of the cast errors, a test that joined them with `meta_corrections`, and `depends_on` lines in silver so the test could skip it.
- **Plain casts in staging, corrections typed.** Simplest, but a bad value fails the build and no correction can fix it.

## Consequences

- Python no longer refuses a correction that is not a number. It is loaded, and the castable test reports it on the next build.
- `ExcelReader` reads every cell as text, so Excel's numbers arrive as the same text a reviewer sees.
- Corrections are judged by the data tests like any other row; they are no longer trusted.
- Corrections are joined after staging's rules, so a row uploaded exactly as candidate shows it does not change. A rule that is not safe to run twice, such as the notes split, has to stay before the join.
- `date_time` is still cast in staging, without a guard: it is the sort order of room groups.
