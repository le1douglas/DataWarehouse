| Number | Exception | Description | File name | Status |
| --- | --- | --- | --- | --- |
| 1 | `FileNotFoundError` | Point `JOURNAL_ENTRIES_CSV` in `config.py` at a file that doesn't exist. | - | pass |
| 2 | `PermissionError` | Open the CSV file in Excel (or another program that locks it) and run the script while it's open. | - | unable to lock file |
| 3 | `IsADirectoryError` | Point `JOURNAL_ENTRIES_CSV` at a folder path instead of a file. | - | unable to trigger `IsADirectoryError`, pointing to directory triggers a `PermissionError` |
| 4 | `pd.errors.EmptyDataError` | Empty CSV file | `journal-entries-empty-no-columns.csv` | pass |
| 5 | `pd.errors.EmptyDataError` exception called manually | CSV file with no rows | `journal-entries-empty-no-rows.csv` | pass |
| 6 | `pd.errors.ParserError` | CSV file with more values in a row than columns defined | `journal-entries-inconsinsent-column-count` | silently drops extra values |
| 7 | `UnicodeDecodeError` | CSV file formatted as UTF-8 with a couple of raw invalid UTF-8 bytes in it (`\xff\xfe`) | `journal-entries-invalid-UTF-8.csv` | pass |
| 8 | - | CSV file formatted as UTF-8 with valid but esoteric characters (`你好 — é`) | `journal-entries-valid-UTF-8.csv` | pass |
| 9 | `UnicodeDecodeError` | CSV file formatted as ANSI with invalid characters (`你好 — é`) | `journal-entries-invalid-ANSI.csv` | pass |
| 10 | - | CSV file formatted as ANSI with valid characters (`€`) | `journal-entries-valid-ANSI.csv` | pass |
| 11 | `ValueError` | CSV file with missing column compared to the DB table | `journal-entries-missing-column.csv` | pass |
| 12 | `ValueError` | CSV file with extra column compared to the DB table | `journal-entries-extra-column.csv` | pass |
| 13 | `ValueError` | CSV file with extra column (with name starting with underscore) compared to the DB table | `journal-entries-extra-column-underscore.csv` | pass |
| 14 | `pandas.errors.DatabaseError` | CSV file with string longer than the allowed `nvarchar` size in the DB | `journal-entries-long-string.csv` | TODO |
| 15 | - | File is not a csv | `journal-entries-wrong-extension.txt` | If formatted like csv still works, but is undefined behaviour. TODO   |
| 16 | - | CSV File has new line inside of text field | `TODO` | TODO   |

