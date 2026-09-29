import sys
from pathlib import Path
from typing import Optional

#TODO make a package one day
ROOT_DIR = Path(__file__).resolve().parent.parent


import pandas as pd
import pytest
from pydantic import Field
FIELD_MAX_LENGHT = 50
value_long =f"this value is longer than {FIELD_MAX_LENGHT}" + ("-" * (FIELD_MAX_LENGHT + 1))

from datawarehouse.reader_csv import CSVReader
from datawarehouse.bronze_record import BronzeRecord

MALFORMED_CSV_DIR = ROOT_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv"


@pytest.fixture
def csv_reader():
    return CSVReader()


@pytest.fixture
def malformed_csv_dir():
    return MALFORMED_CSV_DIR


@pytest.fixture
def expected_valid_dataframe():
    """
    Matches what CSVReader.read produces for valid.csv: every cell a
    plain object (dtype=object), missing cells as Python None.

    """
    return pd.DataFrame({
        "date_time": ["2026-01-01T12:00:00.000000"],
        "subject":   ["default_subject"],
        "notes":     ["default_notes"],
        "type":      ["measurement"],
        "ec":        ["1.00"],
        "ec_pore":   [None],
        "ec_bulk":   [None],
        "ph":        ["7.00"],
        "mc":        [None],
        "temp":      ["25.0"],
        "device":    [None],
        "media":     [None],
        "tags":      [None],
    }, dtype=object)





class FakeRecord_One_Field(BronzeRecord):
    value: Optional[str] = Field(max_length=FIELD_MAX_LENGHT)



class FakeReader_Valid_OneRow:
    def read(self, source: Path) -> pd.DataFrame:
        return pd.DataFrame([{"value": "ok"}])


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
def reader_invalid_too_long_one_row():
    return FakeReader_InvalidTooLong_OneRow


@pytest.fixture
def reader_invalid_too_long_two_rows():
    return FakeReader_InvalidTooLong_TwoRows