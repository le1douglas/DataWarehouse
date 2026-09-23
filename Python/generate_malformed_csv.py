#Generates the malformed CSV files used to test load_journal_entries.py.

import csv
import io
from pathlib import Path

from config import BASE_DIR

OUTPUT_DIR = BASE_DIR / "SampleData" / "drip_drain_csv" / "malformed_csv"

# Column order of Bronze.journal_entries (without the _load_date_time/_source_file debug columns)
COLUMNS = ["date_time", "subject", "notes", "type", "ec", "ec_pore", "ec_bulk",
           "ph", "mc", "temp", "device", "media", "tags"]

# Max length of Bronze.journal_entries.notes (NVARCHAR(400))
NOTES_MAX_LENGTH = 400

LOREM = ("Lorem ipsum dolor sit amet consectetuer adipiscing elit. Aenean commodo ligula eget "
         "dolor. Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes "
         "nascetur ridiculus mus. Donec quam felis ultricies nec pellentesque eu pretium quis "
         "sem. Nulla consequat massa quis enim. Donec pede justo fringilla vel aliquet nec "
         "vulputate eget arcu. In enim justo rhoncus ut imperdiet a venenatis vitae justo. "
         "Nullam dictum felis eu pede mollis pretium. Integer tincidunt. Cras dapibus. Vivamus "
         "elementum semper nisi. Aenean vulputate eleifend tellus.")

# Write one single-row CSV file and return its path.
# To write bytes that are not valid in the target encoding:
#  - invalid UTF-8: put lone surrogates in a field ("\\udcff\\udcfe") and set errors="surrogateescape"
# exisisting files with same name are overwritten.
    
def write_csv(
    file_name: str,
    *, #subsequent parameters must be called by name
    file_extension: str = "csv",

    # --- the row: defaults are one valid measurement, override only what is malformed ---
    # Passing "" gives an empty value (a normal, valid empty field).
    # Passing None for a column omits it from both the header and the row (a "missing column").
    
    date_time: str | None = "2026-01-01T12:00:00.000000",
    subject: str | None = "default_subject",
    notes: str | None = "default_notes",
    type_: str | None = "measurement",  # added trailing underscore to not conflict with python keyword
    ec: str | None = "1.00",
    ec_pore: str | None = "",
    ec_bulk: str | None = "",
    ph: str | None = "7.00",
    mc: str | None = "",
    temp: str | None = "25.0",
    device: str | None = "",
    media: str | None = "",
    tags: str | None = "",
   


    # --- structural malformations (not tied to a single field) ---
    extra_columns: dict[str, str] | None = None,  # added to the header AND the row
    extra_values: tuple[str, ...] = (),           # added to the row only (header stays the same, creates mismatch)
    include_header: bool = True,
    include_row: bool = True,
    add_quotes: bool = False, #adds quotes to every field, reagrdless if its necessary or not

    # --- encoding / file level ---
    encoding: str = "utf-8",
    errors: str = "strict",
    newline: str = "\r\n",
    output_dir: Path = OUTPUT_DIR,
) -> Path:
  

    values = dict(zip(COLUMNS, [date_time, subject, notes, type_, ec, ec_pore, ec_bulk,
                                ph, mc, temp, device, media, tags]))
    #potentially takes out columns
    present = [c for c in COLUMNS if values[c] is not None]
    #potentially adds columns
    header = present + list((extra_columns or {}).keys())

    #row = values in present columns + values in added columns + extra "orphan" values without column
    row = [values[c] for c in present] + list((extra_columns or {}).values()) + list(extra_values)

    # csv.writer handles quoting (commas, quotes and newlines inside a field)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator=newline, quoting=csv.QUOTE_ALL if add_quotes else csv.QUOTE_MINIMAL)
    if include_header:
        writer.writerow(header)
    if include_row:
        writer.writerow(row)

    text = buffer.getvalue()

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{file_name}.{file_extension}"
    path.write_bytes(text.encode(encoding, errors=errors))
    print(f"Wrote {path.name} ({path.stat().st_size} bytes)")
    return path

# Copy a file made by write_csv() to '<name>-unquoted.<ext>' 
# and remove the quotes around the value of one column in the data row.
# all other columns keep the quotes
# only pass utf-8 files
def generate_unquoted_version(path: Path, column_name: str = "notes") -> Path | None:

    # real value of the column in the first data row (DictReader skips the header)
    with path.open(newline="", encoding="utf-8") as f:
        value = next(csv.DictReader(f))[column_name]

    # raw text of the file (newline="" so \r\n is not translated)
    with path.open(newline="", encoding="utf-8") as f:
        csv_as_text = f.read()

    # find the field in the raw text, including its quotes.
    # In the file every " inside the value is written as "", every other character is the same
    quoted_field = '"' + value.replace('"', '""') + '"'
    first = csv_as_text.find(quoted_field)      # index of the opening quote
    if first == -1:
        raise ValueError(f"{path.name}: '{column_name}' is not quoted")
    
    last = first + len(quoted_field) - 1                    # index of the closing quote

    # drop the quote at both ends, turn "" into " inside the field only
    new_text = (csv_as_text[:first]
                + value
                + csv_as_text[last + 1:])

    new_path = path.with_stem(path.stem + "-unquoted")
    with new_path.open("w", newline="", encoding="utf-8") as f:
        f.write(new_text)
    print(f"Wrote {new_path.name} ({new_path.stat().st_size} bytes)")
    return new_path



def main():
    # --- NORMAL VALID CSV ---

    write_csv("valid")
    
    
    # --- CSV STRUCTURE ERRORS ---

    # completely empty file (0 bytes)
    write_csv("empty-no-columns",
              include_header=False,
              include_row=False)

    # header but no data rows
    write_csv("empty-no-rows",
              include_row=False)

    # row has more values than the header has columns
    write_csv("extra-value",
              extra_values=("EXTRA", "EXTRA2", "EXTRA3", "EXTRA4"))

    #TODO write "missing-value"

    # 15: not a .csv file, but valid CVS structure
    write_csv("wrong-extension", 
              file_extension="txt",
              notes="txt file")


    # --- ENCODING ERRORS ---

    # invalid UTF-8
    write_csv("invalid-UTF-8",
              notes="\udcff\udcfe bad bytes",
              errors="surrogateescape")

    # UTF-8 with BOM (Excel "CSV UTF-8"): first column name becomes '\ufeffdate_time'
    write_csv("UTF-8-bom",
              encoding="utf-8-sig")

    # UTF-16: invalid start byte for a UTF-8 reader
    write_csv("UTF-16",
              encoding="utf-16")

    # valid ANSI (cp1252) but invalid UTF-8: the euro sign is the single byte [0x80] in cp1252, but [e2 82 ac] in UTF-8
    write_csv("valid-ANSI",
              notes="valid € ansi",
              encoding="cp1252")


    # --- SCHEMA ERRORS ---

    # missing column (tags) compared to the DB table
    write_csv("missing-column",
              tags=None)

    # extra column compared to the DB table
    write_csv("extra-column",
              extra_columns={"extra_col": "extra_col_value"})

    # extra column compared to the DB table, whose name starts with an underscore (looks like a debug column)
    write_csv("extra-column-underscore",
              extra_columns={"_extra_col": "extra_col_value"})

    # notes one character longer than NVARCHAR(...)
    write_csv("long-string",
              notes=LOREM[: NOTES_MAX_LENGTH + 1])

    # --- QUOTES TESTS ---
 
    generate_unquoted_version(
    write_csv("comma",
                  notes="this text contains, a comma",
                  add_quotes= True)
    )

    generate_unquoted_version(
    write_csv("quotes",
                notes="this text contains \"escaped quotes",
                add_quotes= True)
    )


    generate_unquoted_version(
    write_csv(
        "tab",
        notes="this text contains\ta tab",
        add_quotes=True)
    )

    generate_unquoted_version(
    write_csv("punctuation",
                notes="this text contains common punctuation except comma quotes and tab \;!@#$%^&*()_+-=[]\{\}|;'^:./<>?€",
                add_quotes= True)
    )    

    generate_unquoted_version(
    write_csv("newline",
                notes="this text contains\n\ra carriage return and newline",
                add_quotes= True)
    )    

    generate_unquoted_version(
    write_csv("esoteric-unicodes",
                notes="this text contains esoteric unicodes: 🚀 Café naïve. مرحبا العالم! 你好世界 — ",
                add_quotes= True)
    )  




if __name__ == "__main__":
    main()