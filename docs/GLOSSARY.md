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
What identifies a journal entry: an identifier it is given when it is received, unique across every dataset, that never changes and follows it through every layer.
_Avoid_: Natural key. The date and time and the device are unique together, but they do not identify a journal entry.

**Room**:
The growing room a journal entry was measured in.

**Spot**:
The place in a room where a journal entry was measured: drip left, drip right, drain left or drain right.
_Avoid_: Position, location

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
What happens to a file that fails a data test: all of it leaves bronze, the user is told each failing line, and it is fixed where it came from. One bad row refuses the whole file.
_Avoid_: Rejected, flagged

**File failure**:
A failure of the file as a whole, such as too few rows, with no line to point at.
