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


#QUOTE_ALL = csv.QUOTE_ALL #quote all fields, even if not strictly necessary, across the whole file
QUOTE_MINIMAL = csv.QUOTE_MINIMAL #quote fields only if necessary, across the whole file
QUOTE_INVALID = -1 #generate invalid quotes


def encode_and_save(file_name: str,
                    header: list[str], 
                    row: list[str], 
                    newline: str = "\r\n",     
                    quoting: int = QUOTE_MINIMAL, #see QUOTE_* consts
                    column_to_unquote : str = "notes", #what column to invalidate if QUOTE_INVALID is used
                    output_dir: Path = OUTPUT_DIR, 
                    file_extension: str = "csv", 
                    encoding: str = "utf-8",
                    errors: str = "strict"):



    # csv.writer handles quoting (commas, quotes and newlines inside a field)

    if quoting == QUOTE_INVALID:
        csv_quoting= csv.QUOTE_ALL
    elif quoting == QUOTE_MINIMAL:
        csv_quoting = csv.QUOTE_MINIMAL
    else: csv_quoting = quoting #in case someone wants to pass another csv.Quote_* we just pass it along


    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator=newline, quoting= csv_quoting)
    writer.writerow(header)
    writer.writerow(row)
    content = buffer.getvalue() 

    # modify row so it has an invalid unquoted field 
    # all other columns keep the quotes
    if quoting == QUOTE_INVALID:
        # Real value of the column in the first data row
        value = next(csv.DictReader(io.StringIO(content)))[column_to_unquote]
        

        # find the field in the raw text, including its quotes.
        quoted_field = '"' + value.replace('"', '""') + '"'         # In the file every " inside the value is written as "", every other character is the same
        first = content.find(quoted_field)      # index of the opening quote
        if first == -1:
            raise ValueError(f"{file_name}: '{column_to_unquote}' is not quoted")

        last = first + len(quoted_field) - 1                    # index of the closing quote

        # drop the quote at both ends, turn "" into " inside the field only
        content = (content[:first]
                    + value
                    + content[last + 1:])

    #write to storage
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{file_name}.{file_extension}"
    path.write_bytes(content.encode(encoding, errors=errors))
    print(f"Wrote {path.name} ({path.stat().st_size} bytes)")


def generate_dict(date_time: str | None = "2026-01-01T12:00:00.000000",
                  subject: str | None = "default_subject",
                  notes: str | None = "default_notes",
                  type: str | None = "measurement",  # added trailing underscore to not conflict with python keyword
                  ec: str | None = "1.00",
                  ec_pore: str | None = "",
                  ec_bulk: str | None = "",
                  ph: str | None = "7.00",
                  mc: str | None = "",
                  temp: str | None = "25.0",
                  device: str | None = "",
                  media: str | None = "",
                  tags: str | None = "",) -> dict:

    values = {key: value for key, value in locals().items() if value is not None}
    return values

def getHeader(content: dict) -> list[str]:
    return list(content.keys())

def getRow(content: dict) -> list[str]:
    return list(content.values())    


def main():

    valid_dict = generate_dict()
    valid_header = getHeader(valid_dict)
    valid_row = getRow(valid_dict)

    # --- NORMAL VALID CSV ---

  
    encode_and_save("valid", valid_header, valid_row)

    
    # --- CSV STRUCTURE ERRORS ---

    # completely empty file (0 bytes)
    encode_and_save("empty-no-columns", [], [])


    # header but no data rows
    encode_and_save("empty-no-rows", valid_header, [])

    # row has more values than the header has columns
    my_row = valid_row.copy()
    my_row.append("EXTRA")
    my_row.append("EXTRA2")
    my_row.append("EXTRA3")
    encode_and_save("extra-value", valid_header, my_row)
    

    # row has lass values than the header has columns
    my_row = valid_row.copy()
    my_row.remove("default_subject")
    my_row.remove("default_notes")
    encode_and_save("missing-value", valid_header, my_row)


    # not a .csv file, but valid CVS structure
    encode_and_save("wrong-extension", valid_header, valid_row, file_extension="txt")


    # # --- ENCODING ERRORS ---
    my_dict= generate_dict(notes="\udcff\udcfe bad bytes")
    encode_and_save("invalid-UTF-8", getHeader(my_dict), getRow(my_dict), errors= "surrogateescape" , encoding= "utf-8")

    # # UTF-8 with BOM (Excel "CSV UTF-8"): first column name becomes '\ufeffdate_time'
    encode_and_save("UTF-8-bom", valid_header, valid_row, encoding= "utf-8-sig")

    # # valid UTF-16: invalid start byte for a UTF-8 reader
    encode_and_save("UTF-16", valid_header, valid_row, encoding= "utf-16")


    # # valid ANSI (cp1252) but invalid UTF-8: the euro sign is the single byte [0x80] in cp1252, but [e2 82 ac] in UTF-8
    my_dict = generate_dict(notes="valid € ansi")
    encode_and_save("valid-ANSI", getHeader(my_dict), getRow(my_dict), encoding="cp1252")


    # # --- SCHEMA ERRORS ---

    # # missing column (tags) compared to the DB table
    my_dict = generate_dict(date_time=None)
    encode_and_save("missing-column", getHeader(my_dict), getRow(my_dict))

    
    # # extra column compared to the DB table
    my_header = valid_header.copy()
    my_header.append("extra_col")
    my_row = valid_row.copy()
    my_row.append("extra_col_value")
    encode_and_save("extra-column", my_header, my_row)



    # # extra column compared to the DB table, whose name starts with an underscore (looks like a debug column)
    my_header = valid_header.copy()
    my_header.append("_extra_col")
    my_row = valid_row.copy()
    my_row.append("extra_col_value")
    encode_and_save("extra-column-underscore", my_header, my_row)

    # # notes one character longer than NVARCHAR(...)
    # write_csv("long-string",
    #           notes=LOREM[: NOTES_MAX_LENGTH + 1])
    my_dict = generate_dict(notes=LOREM[: NOTES_MAX_LENGTH + 1])
    encode_and_save("long-string", getHeader(my_dict), getRow(my_dict))

    # # --- QUOTES TESTS ---
 
    quotes_tests={
                    "comma": "this text contains, a comma",
                    "quotes":"this text contains \"escaped quotes",
                    "tab":"this text contains\ta tab",
                    "punctuation":"this text contains common punctuation except comma quotes and tab \;!@#$%^&*()_+-=[]\{\}|;'^:./<>?€",
                    "newline":"this text contains\n\ra carriage return and newline",
                    "esoteric-unicodes":"this text contains esoteric unicodes: 🚀 Café naïve. مرحبا العالم! 你好世界 — "
                    }
    for file_name, test_string in quotes_tests.items():
        my_dict = generate_dict(notes=test_string)
        encode_and_save(file_name, getHeader(my_dict), getRow(my_dict))
        encode_and_save(file_name+"-unquoted", getHeader(my_dict), getRow(my_dict), quoting=QUOTE_INVALID)





if __name__ == "__main__":
    main()