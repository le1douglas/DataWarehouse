import pytest
from pydantic import ValidationError

from datawarehouse.bronze_record import BronzeRecord


@pytest.mark.parametrize(
    "raw_value, expected",
    [
        ("", None),                      # empty string is the ONLY thing normalized to None
        ("normal text", "normal text"),  # ordinary text passes through untouched
        ("N/A", "N/A"),                  # explicit "not applicable" marker is preserved, not nulled
        ("n/a", "n/a"),                  # lowercase variant also preserved as-is, no normalization
        ("null", "null"),                # the literal word "null" is just text here, not a null value
        ("None", "None"),                # same thing for "None"
        (" ", " "),                      # whitespace-only is left alone, not treated as empty
    ],
)
def test_empty_string_to_null_parametrized(record_one_field, raw_value, expected):
    record = record_one_field(
        value=raw_value,
        meta_extract_date_time="2026-01-01T00:00:00", #unused
        meta_source="test", #unused
    )
    assert record.value == expected

#float(nan) is the internal representation of panda's pd.NA
def test_empty_string_to_null_nan(record_one_field):
    with pytest.raises(ValidationError, match="received a pandas NaN value directly"):
        record_one_field(
            value=float("nan"),
            meta_extract_date_time="2026-01-01T00:00:00", #unused
            meta_source="test", #unused
        )