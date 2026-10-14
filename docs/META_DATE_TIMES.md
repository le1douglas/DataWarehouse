# Date-times in the meta tables

Every meta table holds facts as `(row_id, kind, description)`. This file lists the facts whose description is a
date-time, and how each one behaves. Only the two inputs have a meta table; the layers built by dbt have none.

## Overview

| Meta table | `kind` | Written by | Clock | Written when | Changes later? |
|---|---|---|---|---|---|
| `dev_bronze.meta_bronze` | `extract_date_time` | Python, `CSVReader` | Python `datetime.now()`, local time of the machine running the load | When the CSV is read, just before the insert. The same value for every row of the file | No: bronze only inserts |
| `dev_corrections.meta_corrections` | `meta_reviewed_date_time`, the header of the workbook's last column | Python, `ExcelReader` | The reviewer's Excel / Power Query | When the reviewer reviewed the row, not when it was loaded | Yes: the load upserts on `(row_id, kind)`, so every upload of the row overwrites it |

## What the date-times mean

For bronze the date-time is when the row was received. For corrections it is not an entry time: it is the last time
the reviewer reviewed the row.

## Caveats

- The bronze description has the format `YYYY-MM-DD HH24:MI:SS`, without a time zone.
- The corrections date-time is not normalised: its `kind` is the column header, because `ExcelReader` splits the
  metadata by position, and its description is the text `ExcelReader` reads from the cell. It can carry fractional
  seconds and nothing checks that it is a date-time.
