# Class diagram

The classes and generic types of `src/datawarehouse`, each class with all its attributes and methods, plus the one module that has functions of its own. Read it from top to bottom: the script that starts a load is at the top, the `Loader`, the readers and the database are below it, and the records that describe one row are at the bottom, with one base class per layer and one record for a row of a meta table. `config.py` and every type that comes from a library or from Python itself are left out.

```mermaid
---
title: datawarehouse
---
classDiagram
    direction TB

    class load_journal_entries {
        <<module>>
        + load_bronze()
        + load_corrections()
        + main()
    }

    class Loader {
        + load(source: Path, reader: Callable[[], ExternalReader], record_model: type[RecordT]) RecordSet[RecordT]$
    }

    class PostgreSQLDatabase {
        + str server
        + str name
        + str user
        + int port
        + Engine engine
        - \_\_init__(db_server: str, db_name: str, db_user: str, db_password: str, db_port: int)
        + connect()
        + table_exists(layer: str, table_name: str) bool
        + load_to_dev_bronze(table_name: str, record_set: RecordSet, meta_table_name: str, dataset: str, metadata: dict[str, str])
        + load_to_dev_corrections(table_name: str, record_set: RecordSet, key_columns: list[str], meta_table_name: str, meta_record_set: RecordSet[MetaRecord])
        - \_load_to_corrections(layer: str, table_name: str, record_set: RecordSet, key_columns: list[str], meta_table_name: str, meta_record_set: RecordSet[MetaRecord])
        - \_validate_same_row_ids(record_set: RecordSet, meta_record_set: RecordSet[MetaRecord])
        - \_upsert_with_metadata(conn: Connection, layer: str, table_name: str, record_set: RecordSet, key_columns: list[str], meta_table_name: str, meta_record_set: RecordSet[MetaRecord]) tuple[int, int]
        - \_load_to_bronze(layer: str, table_name: str, record_set: RecordSet, meta_table_name: str, dataset: str, metadata: dict[str, str])
        - \_insert_with_metadata(conn: Connection, layer: str, table_name: str, record_set: RecordSet, meta_table_name: str, dataset: str, metadata: dict[str, str]) tuple[int, int]
    }

    class ExternalReader {
        <<protocol>>
        + read(source: Path) pd.DataFrame
    }

    class CSVReader {
        - \_\_init__()
        + read(source: Path) pd.DataFrame
        - \_validate_fields_number_equals_columns_number(csv_path: Path)
        - \_validate_is_csv_file(source: Path)
    }

    class ExcelReader {
        + str sheet_name
        - \_\_init__(sheet_name: str)
        + read(source: Path) pd.DataFrame
        - \_validate_is_excel_file(source: Path)
    }

    class RecordSet~RecordT~ {
        <<pydantic model>>
        + list[RecordT] rows
        - \_not_empty() RecordSet[RecordT]
    }

    class RecordT {
        <<TypeVar>>
    }

    class Record {
        <<pydantic model>>
        + ConfigDict model_config
        - \_empty_string_to_null(data: dict) dict$
        + add_metadata(df: pd.DataFrame, source: Path) pd.DataFrame$
    }

    class BrnzRecord {
        <<pydantic model>>
        + add_metadata(df: pd.DataFrame, source: Path) pd.DataFrame$
        + load_metadata(source: Path) dict[str, str]$
    }

    class CorrRecord {
        <<pydantic model>>
        + add_metadata(df: pd.DataFrame, source: Path) pd.DataFrame$
    }

    class BrnzRecordJournalEntries {
        <<pydantic model>>
        + str date_time
        + str subject
        + Optional[str] notes
        + Optional[str] type
        + str ec
        + Optional[str] ec_pore
        + Optional[str] ec_bulk
        + str ph
        + Optional[str] mc
        + Optional[str] temp
        + Optional[str] device
        + Optional[str] media
        + Optional[str] tags
    }

    class MetaRecord {
        <<pydantic model>>
        + UUID row_id
        + str dataset
        + str kind
        + str description
        + add_metadata(df: pd.DataFrame, source: Path) pd.DataFrame$
    }

    class CorrRecordJournalEntries {
        <<pydantic model>>
        + UUID row_id
        + datetime date_time
        + str subject
        + Optional[str] type
        + Optional[Decimal] ml
        + Optional[Decimal] ec
        + Optional[Decimal] ph
        + Optional[Decimal] temp
        + Optional[str] notes
        + Optional[str] room
    }

    load_journal_entries ..> Loader : calls
    load_journal_entries ..> PostgreSQLDatabase : creates
    load_journal_entries ..> BrnzRecord : asks the metadata of the load

    Loader ..> ExternalReader : reads with
    Loader ..> RecordSet : creates
    Loader ..> RecordT : validates into
    PostgreSQLDatabase ..> RecordSet : writes
    PostgreSQLDatabase ..> MetaRecord : creates for bronze, writes
    Loader ..> MetaRecord : validates the corrections metadata into

    ExternalReader <|.. CSVReader
    ExternalReader <|.. ExcelReader

    RecordSet "1" *-- "1..*" RecordT : rows
    RecordT ..> Record : bound to

    Record <|-- BrnzRecord
    Record <|-- CorrRecord
    Record <|-- MetaRecord
    BrnzRecord <|-- BrnzRecordJournalEntries
    CorrRecord <|-- CorrRecordJournalEntries
```

## Legend

- **`<<module>>`:** a module that has functions of its own, drawn as a box with those functions. A module that only holds a class is not drawn.
- **`<<pydantic model>>`:** a class that inherits from pydantic's `BaseModel`, directly or through `Record`. Pydantic validates every object of the class when it is created.
- **`<<protocol>>`:** a `Protocol`. It describes the methods a class must have, and no class needs to inherit from it.
- **`<<TypeVar>>`:** a generic type, a placeholder for one specific class.
- **`+` and `-`:** a public member, and a member whose name starts with an underscore.
- **Underlined method:** a `@staticmethod` or a `@classmethod`.
- **Solid line with a hollow arrowhead:** the lower class inherits from the upper one.
- **Dashed line with a hollow arrowhead:** the lower class has the methods the protocol above it asks for.
- **Line with a filled diamond:** the class at the diamond holds objects of the other type. The numbers say how many: one `RecordSet` holds one or more rows.
- **Dashed line with an open arrowhead and a label:** the upper box uses the lower one in the way the label says.
- **Not drawn:** `config.py`, and the types from the standard library and from installed libraries. Their names appear only as the type of an attribute, a parameter or a return value.
