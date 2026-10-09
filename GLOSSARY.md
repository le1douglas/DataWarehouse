# Data Warehouse

A warehouse for sensor measurements taken in the growing rooms, built so that bad data is never published and a person can fix it without touching what was received.

## Language

### Measurements

**Journal entry**:
One measurement recorded in the Bluelab edenic app, with its volume, EC, pH and temperature.

**Subject**:
The name of the sensor that took a journal entry, such as `ONE-A1F0` for a Bluelab OnePen.

**Key**:
What identifies a journal entry: its date and time to the second, together with its subject.

**Room**:
The growing room a journal entry was measured in.
_Avoid_: Tag

**Room group**:
The consecutive journal entries measured in the same room, normally four, one per position.

**Position**:
The place in a room where a journal entry was measured: drip left, drip right, drain left or drain right.

### Layers

**Bronze**:
The data exactly as it was received.

**Staging**:
Bronze with automatic fixes applied and values converted to their types.

**Candidate**:
The proposal for silver: staging with corrections applied and room groups and positions derived. It is what the data tests judge.

**Audit**:
The record of which journal entries failed which data tests.

**Silver**:
The published result. It changes only when the candidate passes every data test.

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
A reviewer's replacement for a whole journal entry, kept apart from bronze and applied again on every build.

**Cast error**:
A received value that could not be converted to its type.

**Meta column**:
A column that describes how a row was handled rather than what was measured.
