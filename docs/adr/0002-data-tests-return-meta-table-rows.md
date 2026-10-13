# Data tests return meta table rows, not candidate rows

A data test used to return whole candidate rows, so a failure table showed a reviewer the values of the row that failed. Every data test now returns `row_id`, `kind` and `description`, typed like a meta table, with `kind = 'failed_test'` and the rule as the description. We chose this because the failure tables can then be combined with a plain `union all`, whatever a test checks and whichever candidate it reads, and because the candidate no longer has to carry columns only for a test to return them.

## Considered Options

- **Whole candidate rows.** A failure table can be read on its own, but every test has the columns of its candidate, so combining them needed the `create_audit_views` macro to compare columns and leave out the tests that did not fit.
- **One row per cast error in the cast test**, with the description of the cast error. Rejected: the text is already in `meta_staging`, and the table would hold the same fact twice.

## Consequences

- A failure table says which journal entry failed which rule and nothing more. The values come from the candidate and the cast error texts from `meta_staging`, joined on `row_id`.
- A generic dbt test (`not_null`, `unique`) does not return this shape, so it does not fit in a `union all` with the others.
