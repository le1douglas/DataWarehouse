import sys
from pathlib import Path
from typing import Optional

#TODO make a package one day
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "Python"))


import pandas as pd
import pytest
from pydantic import Field

from bronze_record import BronzeRecord

FIELD_MAX_LENGHT = 50
value_long =f"this value is longer than {FIELD_MAX_LENGHT}" + ("-" * (FIELD_MAX_LENGHT + 1))


class FakeRecord_One_Field(BronzeRecord):
    value: Optional[str] = Field(max_length=FIELD_MAX_LENGHT)



class FakeReader_Valid_OneRow:
    def read(self, source: Path) -> pd.DataFrame:
        return pd.DataFrame([{"value": "ok"}])


class FakeReader_Empty:
    def read(self, source: Path) -> pd.DataFrame:
        return pd.DataFrame(columns=["value"])


class FakeReader_InvalidTooLong_OneRow:
    def read(self, source: Path) -> pd.DataFrame:
        #TODO
        return pd.DataFrame([{"value": value_long}])


class FakeReader_InvalidTooLong_TwoRows:
    def read(self, source: Path) -> pd.DataFrame:
        return pd.DataFrame([
            {"value": value_long},
            {"value": value_long},
        ])


@pytest.fixture
def record_one_field():
    return FakeRecord_One_Field


@pytest.fixture
def reader_valid_one_row():
    return FakeReader_Valid_OneRow


@pytest.fixture
def reader_empty():
    return FakeReader_Empty


@pytest.fixture
def reader_invalid_too_long_one_row():
    return FakeReader_InvalidTooLong_OneRow


@pytest.fixture
def reader_invalid_too_long_two_rows():
    return FakeReader_InvalidTooLong_TwoRows