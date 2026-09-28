

import sys
from pathlib import Path

import pandas as pd
import pandas.testing as pdt
import pytest


# ---- baseline: does an ordinary file parse into the right shape at all ----

def test_valid_csv_parses_correctly(csv_reader, malformed_csv_dir, expected_valid_dataframe):
    df = csv_reader.read(malformed_csv_dir / "valid.csv")

    assert len(df) == 1
    pdt.assert_frame_equal(df, expected_valid_dataframe)


# ---- section 1: "strange/tricky" content in the "notes" field ----
# text fields surrounded by the text delimiter ("): all should be valid
# text fields NOT surrounded by the delimiter: fail only when the text itself contains a field delimiter or a newline

CONTENT_TEST_CASES = [
    ("esoteric-unicodes.csv", "this text contains esoteric unicodes: 🚀 Café naïve. مرحبا العالم! 你好世界 — ", None),
    ("newline.csv",           "this text contains\n\ra carriage return and newline",                            pd.errors.ParserError),
    ("punctuation.csv",       "this text contains common punctuation except comma quotes and tab \\;!@#$%^&*()_+-=[]\\{\\}|;'^:./<>?€", None),
    ("quotes.csv",            "this text contains \"escaped quotes",                                            None),
    ("tab.csv",               "this text contains\ta tab",                                                      None),
    ("comma.csv",             "this text contains, a comma",                                                    pd.errors.ParserError),
]


@pytest.mark.parametrize("file_name, expected_notes, expected_exception_when_unquoted", CONTENT_TEST_CASES)
def test_special_characters_quoted(csv_reader, malformed_csv_dir, expected_valid_dataframe,
                                    file_name, expected_notes, expected_exception_when_unquoted):
    expected_df = expected_valid_dataframe.copy()
    expected_df["notes"] = pd.Series(expected_notes, dtype=object) #change "note", while maintaing the right type
    df = csv_reader.read(malformed_csv_dir / file_name)

    # full-frame comparison: a bad "notes" parse can shift/bleed into
    # neighboring columns (e.g. an unescaped comma), so every column is
    # checked, not just notes itself
    pdt.assert_frame_equal(df, expected_df)


@pytest.mark.parametrize("file_name, expected_notes, expected_exception_when_unquoted", CONTENT_TEST_CASES)
def test_special_characters_unquoted(csv_reader, malformed_csv_dir, expected_valid_dataframe,
                                      file_name, expected_notes, expected_exception_when_unquoted):
    unquoted_file_name = Path(file_name).stem + "-unquoted.csv"

    if expected_exception_when_unquoted is None:
        expected_df = expected_valid_dataframe.copy()
        expected_df["notes"] = pd.Series(expected_notes, dtype=object) #change "note", while maintaing the right type

        

        df = csv_reader.read(malformed_csv_dir / unquoted_file_name)

        pdt.assert_frame_equal(df, expected_df)
    else:
        with pytest.raises(expected_exception_when_unquoted):
            csv_reader.read(malformed_csv_dir / unquoted_file_name)


# ---- section 2: text encoding ----

def test_utf_8(csv_reader, malformed_csv_dir, expected_valid_dataframe):
    df = csv_reader.read(malformed_csv_dir / "valid.csv")
    pdt.assert_frame_equal(df, expected_valid_dataframe)


def test_utf_8_bom(csv_reader, malformed_csv_dir, expected_valid_dataframe):
    df = csv_reader.read(malformed_csv_dir / "UTF-8-bom.csv")
    pdt.assert_frame_equal(df, expected_valid_dataframe)


def test_invalid_utf_8(csv_reader, malformed_csv_dir):
    with pytest.raises(UnicodeDecodeError):
        csv_reader.read(malformed_csv_dir / "invalid-UTF-8.csv")


def test_utf_16(csv_reader, malformed_csv_dir):
    with pytest.raises(UnicodeDecodeError):
        csv_reader.read(malformed_csv_dir / "UTF-16.csv")


def test_valid_ansi(csv_reader, malformed_csv_dir):
    with pytest.raises(UnicodeDecodeError):
        csv_reader.read(malformed_csv_dir / "valid-ANSI.csv")


# ---- section 3: file-level errors ----

def test_wrong_extension(csv_reader, malformed_csv_dir):
    with pytest.raises(ValueError, match="Wrong file extension"):
        csv_reader.read(malformed_csv_dir / "wrong-extension.txt")


def test_file_not_found(csv_reader, malformed_csv_dir):
    with pytest.raises(FileNotFoundError):
        csv_reader.read(malformed_csv_dir / "this-file-does-not-exists.csv")


def test_empty_file(csv_reader, malformed_csv_dir):
    with pytest.raises(pd.errors.EmptyDataError):
        csv_reader.read(malformed_csv_dir / "empty-no-header.csv")


@pytest.mark.skipif(sys.platform != "win32", reason="msvcrt file locking is Windows-specific")
def test_locked_file_win(csv_reader, malformed_csv_dir):
    import msvcrt  # imported here, not at module level, so non-Windows machines don't choke on it

    locked_path = malformed_csv_dir / "valid.csv"
    with open(locked_path, "r+b") as f:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)  # lock 1 byte, non-blocking
        try:
            with pytest.raises(PermissionError):
                csv_reader.read(locked_path)
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)  # always unlock before closing


#TODO unable to test on windows, find mac or linux to test it on
#@unittest.skipIf(sys.platform == "win32", "")
#def test_locked_file_posix(self):
#    pass


@pytest.mark.skipif(sys.platform != "win32", reason="PermissionError on directory is Windows-specific; POSIX raises IsADirectoryError instead")
def test_directory_named_csv_win(csv_reader, malformed_csv_dir):
    directory_as_csv = malformed_csv_dir / "not-a-real-file.csv"
    directory_as_csv.mkdir(exist_ok=True)
    try:
        with pytest.raises(PermissionError):
            csv_reader.read(directory_as_csv)
    finally:
        directory_as_csv.rmdir()


#TODO unable to test on windows, find mac or linux to test it on
@pytest.mark.skipif(sys.platform == "win32", reason="IsADirectoryError on directory is POSIX-specific; Windows raises PermissionError instead")
def test_directory_named_csv_posix(csv_reader, malformed_csv_dir):
    directory_as_csv = malformed_csv_dir / "not-a-real-file.csv"
    directory_as_csv.mkdir(exist_ok=True)
    try:
        with pytest.raises(IsADirectoryError):
            csv_reader.read(directory_as_csv)
    finally:
        directory_as_csv.rmdir()





# ---- section 4: structural row/column-count mismatch ----

def test__validate_fields_number_equals_columns_number_extra_value(csv_reader, malformed_csv_dir):
    with pytest.warns(pd.errors.ParserWarning): #we acknowledge that panda gives us a warning,. In practice we dont care, as we raise our own exception
            with pytest.raises(pd.errors.ParserError, match="CSV has a row whose number of fields differs from the header"):
                csv_reader.read(malformed_csv_dir / "extra-value.csv")


def test__validate_fields_number_equals_columns_number_missing_value(csv_reader, malformed_csv_dir):
    with pytest.raises(pd.errors.ParserError, match="CSV has a row whose number of fields differs from the header"):
        csv_reader.read(malformed_csv_dir / "missing-value.csv")