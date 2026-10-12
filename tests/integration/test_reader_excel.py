import pandas as pd
import pandas.testing as pdt
import pytest

from datawarehouse.reader_excel import ExcelReader


# a workbook with two sheets, like the corrections workbook: the corrections and their metadata
@pytest.fixture
def workbook(tmp_path):
    path = tmp_path / "workbook.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"subject": ["ONE-A1F0", "ONE-B2E1"], "notes": ["N/A", None]}).to_excel(
            writer, sheet_name="first", index=False
        )
        pd.DataFrame({"kind": ["reviewed_by"], "description": ["reviewer"]}).to_excel(
            writer, sheet_name="second", index=False
        )
    return path


# every cell is a plain object, an empty cell is None, and "N/A" is not a missing value
def test_reads_the_sheet_it_was_given(workbook):
    df = ExcelReader("first").read(workbook)

    expected = pd.DataFrame({"subject": ["ONE-A1F0", "ONE-B2E1"], "notes": ["N/A", None]}, dtype=object)
    pdt.assert_frame_equal(df, expected)


def test_reads_another_sheet_of_the_same_workbook(workbook):
    df = ExcelReader("second").read(workbook)

    expected = pd.DataFrame({"kind": ["reviewed_by"], "description": ["reviewer"]}, dtype=object)
    pdt.assert_frame_equal(df, expected)


def test_sheet_that_does_not_exist_is_refused(workbook):
    with pytest.raises(ValueError):
        ExcelReader("missing").read(workbook)


def test_file_that_is_not_xlsx_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Wrong file extension"):
        ExcelReader("first").read(tmp_path / "workbook.csv")
