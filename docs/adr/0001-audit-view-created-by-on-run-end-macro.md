# The audit view is created by an on-run-end macro, not by a dbt model

Each data test stores its failing rows in its own table in `dev_audit`, and those tables stay the source of truth for what failed. For Excel (and later other tools) we want one object per candidate model, `aud_<token>`, with one row per flagged row and a `meta_failed_tests` column listing the data tests it failed. We create that view in an `on-run-end` macro that reads the dbt graph, so adding a test file is the only step needed for it to appear in the view.

## Considered options

- **A dbt model that unions the failure tables.** Rejected: a model cannot depend on tests, and dbt-postgres drops every failure table with `cascade` at the start of its test, which drops any view on top of it. The model would disappear on every build.
- **All data tests of a model in one test file**, so the single failure table is the combined result. Rejected: dbt would report one pass/fail for the whole file, and one check per test is the dbt convention.
- **Moving the checks into a model and making the tests thin selects on it.** Rejected: it changes how `dbt build` decides to skip silver, which works today.

## Consequences

- The view is not under `models/`, it does not appear in the dbt lineage, and nothing can `ref()` it.
- Tests are grouped by the model they `ref()`, not by their name. The name only supplies the label in `meta_failed_tests`.
- A data test is left out of the view, with a warning, when it is not on exactly one candidate model or does not return whole candidate rows. Its own failure table is still written.
- After a partial run the view mixes fresh results with older ones from the tests that did not run.
