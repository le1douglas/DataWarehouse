# Data Warehouse

A warehouse for sensor measurements taken in the growing rooms, built so that bad data is never published and a person can fix it without touching what was received.

## Language

### Measurements

**Journal entry**:
One measurement recorded in the Bluelab edenic app, with its volume, EC, pH and temperature.

**Subject**:
The name of the sensor that took a journal entry, such as `ONE-A1F0` for a Bluelab OnePen.

**Key**:
What identifies a journal entry: an identifier it is given when it is received, unique across every dataset, that never changes and follows it through every layer.
_Avoid_: Natural key. The date and time and the subject no longer identify a journal entry.

**Recorded room**:
The room written down with a journal entry when it was measured. It can be missing or wrong, and it is what a reviewer corrects.
_Avoid_: Tag

**Room**:
The growing room of a room group, derived from the recorded rooms. Every journal entry of the group was measured in it.

**Room group**:
Consecutive journal entries that start where the recorded room changes, normally four, one per position.

**Position**:
The place in a room where a journal entry was measured: drip left, drip right, drain left or drain right.

### Layers

**Dataset**:
One kind of data received from a source, such as the journal entries from the edenic app. It is the same dataset in every layer, even though its structure changes from one layer to the next.
_Avoid_: Token

**Input**:
A layer filled from outside the warehouse, which the warehouse reads and never changes. Bronze and corrections are the inputs.

**Bronze**:
The store of all raw data, exactly as received from the sources. An input that has meaning on its own.

**Corrections**:
The latest correction of each journal entry, as uploaded by a reviewer. An input that has meaning only for journal entries already in the warehouse. Earlier corrections are in its snapshot.

**Staging**:
Bronze with automatic fixes applied, in the same shape as a correction. The values stay text, so a value that cannot be converted can still be corrected.

**Candidate**:
The proposal for silver: staging with corrections applied and room groups and positions derived. It is what the data tests judge and what the reviewer sees: silver's rows and columns, before the values are converted to their types.

**Audit**:
The record of which journal entries failed which data tests, and why: one entry per journal entry and failed rule, with the reason the data test gave. It holds no values of the journal entry; those are read from the candidate.

**Failure table**:
What one data test found in its last run: each journal entry that failed it, once, with the reason. The audit combines the failure tables of a dataset, and they stay the source of truth for it.
_Avoid_: Test results, failures on their own

**Snapshot**:
The record of every value the rows of one table have had, kept by the warehouse itself: one version per change, in the same shape as the table it records.
_Avoid_: SCD, slowly changing dimension, history table

**Version**:
One state of a row in a snapshot, valid from the build that first saw it until the build that saw it change or disappear.

**Silver**:
The published result: the candidate with its values converted to their types. It changes only when the candidate passes every data test.

### Review

**Data test**:
A check on the content of the data that every row of the candidate must pass before silver is published.
_Avoid_: Test on its own, which can also mean a unit or integration test of the code

**Flagged row**:
A journal entry that failed a data test and waits for review.

**Review**:
A person inspecting the flagged rows and deciding what their values should be.

**Reviewer**:
The person who does a review.

**Correction**:
A reviewer's replacement for a whole journal entry, kept apart from bronze and applied again on every build. It is not trusted: the data tests judge a corrected journal entry like any other.

**Cast error**:
A value, received or corrected, that cannot be converted to its type. Its journal entry is a flagged row, and silver is not published until a correction fixes it.

**Metadata**:
A fact about how a journal entry was handled rather than what was measured, such as where it came from or who reviewed it.

**Meta column**:
Metadata kept on the journal entry itself, such as who reviewed it. Which data tests it failed is not stored as one: the audit holds one entry per failed rule. Whether a journal entry was corrected is not one: it is read by joining `row_id` to the corrections. The inputs have none: their metadata is in their meta table.

**Kind**:
Which fact a piece of metadata records, such as the source or the reviewer.

**Meta table**:
The store of an input's metadata: bronze and corrections each have one, and it holds only what that input recorded at load time. The layers built by dbt have none.
