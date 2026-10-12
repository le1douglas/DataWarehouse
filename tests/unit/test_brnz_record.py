import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from datawarehouse.brnz_record import BrnzRecord


# bronze metadata is not a column of the row
def test_add_metadata_adds_no_columns():
    df = pd.DataFrame([{"value": "ok"}])

    result = BrnzRecord.add_metadata(df, Path("some/path/to/file.csv"))

    assert list(result.columns) == ["value"]


def test_load_metadata_kinds():
    source = Path("some/path/to/file.csv")

    metadata = BrnzRecord.load_metadata(source)

    assert set(metadata) == {"extract_date_time", "source"}
    assert metadata["source"] == str(source)


# the date and time is text, to the second, with no time zone: 2026-10-12 16:41:07
def test_load_metadata_extract_date_time():
    before = datetime.now().replace(microsecond=0)

    extract_date_time = BrnzRecord.load_metadata(Path("unused"))["extract_date_time"]

    after = datetime.now()

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", extract_date_time)
    assert before <= datetime.fromisoformat(extract_date_time) <= after
