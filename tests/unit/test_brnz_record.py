import re
from datetime import datetime
from pathlib import Path

from datawarehouse.brnz_record import BrnzRecord


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
