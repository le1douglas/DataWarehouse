# Data Warehouse

A warehouse for sensor measurements taken in the growing rooms, built so that bad data is never published: what fails is refused, and fixed where it came from.

## Language

### Measurements

**Journal entry**:
One measurement recorded in the Bluelab edenic app, with its volume, EC, pH and temperature.

**Device**:
The instrument that took a journal entry, such as `ONE-A1F0` for a Bluelab OnePen.
_Avoid_: Subject, sensor

**Key**:
What identifies a row of any dataset, such as a journal entry or a plants batch: an identifier it is given when it is received, unique across every dataset, that never changes and follows it through every layer.
_Avoid_: Natural key. Some columns are unique together, such as the date and time and the device of a journal entry, or the PP number of a plants batch, but they do not identify the row.

**Room**:
A growing room, such as `1.30`: where a journal entry was measured, or where a plants batch is grown. Each room has an assigned stage, such as flowering, and a number of benches.

**Bench**:
The growing table in a room that a journal entry was measured at. A room usually has 7.
_Avoid_: Table, which is an SQL keyword

**Relative position**:
Where on the bench a journal entry was measured: `front` or `back`, `left` or `right`, `up` or `down`, such as `front_left_up`. The bench itself is separate. The source sends it as a spot, such as `drip_left`: always front, `drip` (the solution given to the plants) is up and `drain` (the solution that ran off them) is down.
_Avoid_: Spot, which is the source's column; drip or drain and side, the columns it replaced; position, location

**Absolute position**:
The place in the real world where a journal entry was measured: its room, its bench and its relative position, such as `1.30_4_front_left_up`. Every one that exists is generated from the rooms, their number of benches and the relative positions.
_Avoid_: Spot, position, location

### Plants batches

**Plants batch**:
A group of plants of one strain, grown together in one room, with its planned timeline: when it starts the vegetative stage, and when it starts and ends the flowering stage.
_Avoid_: Plant, which is one of the plants in it; crop, cycle

**PP number**:
What the grower calls a plants batch, such as `PP-000366`: `PP-` and six digits. One plants batch has one PP number. It identifies the batch for the grower, but it is not its key: a plants batch sent again with the same PP number replaces the earlier one.
_Avoid_: Batch id, which suggests the key

**Strain**:
The variety of the plants in a plants batch, such as `WTF`.
_Avoid_: Cultivar

**Vegetative stage**:
The stage in which plants grow leaves and stems before they flower.
_Avoid_: Veg, except in column names

**Flowering stage**:
The stage after the vegetative stage, from the start of flowering until the plants batch is harvested. Only a room whose assigned stage is flowering can hold a plants batch. While a plants batch is flowering, no other batch is planned in its room with the same flowering dates.
_Avoid_: Bloom

**Planned date**:
A date of a plants batch's timeline, as the grower expects it, not as it happened. The dates a stage really started or ended are not recorded yet.
_Avoid_: Measured, actual date

### Layers

**Dataset**:
One kind of data received from a source, such as the journal entries. It is the same dataset in every layer, even though its structure changes from one layer to the next.
_Avoid_: Token

**Bronze**:
The store of all accepted raw data, exactly as received from the sources. It has meaning on its own.

**Staging**:
Bronze with its values converted to their types, and whatever a source needs mapped or fixed automatically. A value that cannot be converted is empty here, so a data test reports it.

**Silver**:
The published result. It changes only when staging passes every data test, and until then keeps its last good version.

**Audit**:
What failed in every run: which row, which data test, which column, and the message.

**Snapshot**:
The record of every value the rows of one table have had, kept by the warehouse itself: one version per change, in the same shape as the table it records.
_Avoid_: SCD, slowly changing dimension, history table

**Version**:
One state of a row in a snapshot, valid from the build that first saw it until the build that saw it change or disappear.

### Checking a file

**Data test**:
A check on the content of the data that must pass before silver is published.
_Avoid_: Test on its own, which can also mean a unit or integration test of the code

**Upload**:
One file going into the warehouse: it is loaded, judged, and either accepted or refused.

**Refused**:
What happens to a file that fails a data test: none of it reaches silver, the user is told each failing row, and it is fixed where it came from. One bad row refuses the whole file. Bronze keeps it, as the record of what arrived.
_Avoid_: Rejected, flagged

**File failure**:
A failure of the file as a whole, such as too few rows, with no line to point at.
