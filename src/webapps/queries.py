import os

from sqlalchemy import MetaData, Table, column, create_engine, func, select, table
from sqlalchemy.dialects.postgresql import Insert, insert

# the same variables as the loader. no defaults: a missing variable stops the app with a KeyError naming it
engine = create_engine(
    f"postgresql+psycopg://{os.environ['POSTGRESQL_USER']}:{os.environ['POSTGRESQL_PASSWORD']}"
    f"@{os.environ['POSTGRESQL_SERVER']}:{os.environ['POSTGRESQL_PORT']}/{os.environ['POSTGRESQL_DB']}"
)

# the columns of information_schema.tables that select_datasets reads
information_schema_tables = table("tables", column("table_schema"), column("table_name"), schema="information_schema")


# a dataset is every table of dw_candidate, without its prefix: the one name of its tables in every layer
def select_datasets() -> list[str]:
    dataset = func.regexp_replace(information_schema_tables.c.table_name, "^cand_", "").label("dataset")
    statement = (
        select(dataset).where(information_schema_tables.c.table_schema == "dw_candidate").order_by(dataset)
    )
    with engine.connect() as connection:
        return list(connection.execute(statement).scalars())


# the rows of candidate, with only the columns of corrections, in their order: what a reviewer can correct.
# every value as text: row_id is a uuid, which the browser cannot receive as is
def select_cand_as_corr(dataset: str) -> tuple[list[str], list[dict]]:

    # a corrections column that candidate does not have raises ValueError naming them: the two tables are out of step.
    cand = get_cand(dataset)
    columns = list(get_corr(dataset).columns.keys())
    missing = [name for name in columns if name not in cand.c]
    if missing:
        raise ValueError(f"{cand.fullname} lacks the corrections columns {missing}")
    statement = select(*(cand.c[name] for name in columns))
    

    
    with engine.connect() as connection:
        rows = [
            {name: None if value is None else str(value) for name, value in row.items()}
            for row in connection.execute(statement).mappings()
        ]

    return columns, rows


# the known errors of each row, by row_id: audit holds one row per error, so a row_id can have several.
# an error is its kind and description, as "kind: description". the row_id is text, like in select_cand_as_corr
def select_aud_errors(dataset: str) -> dict[str, list[str]]:
    aud = get_aud(dataset)
    statement = select(aud.c.row_id, aud.c.kind, aud.c.description).order_by(aud.c.row_id, aud.c.kind)
    errors: dict[str, list[str]] = {}
    with engine.connect() as connection:
        for row_id, kind, description in connection.execute(statement):
            errors.setdefault(str(row_id), []).append(f"{kind}: {description}")
    return errors


# the edited rows go into corrections, replacing any earlier correction of the same row_id, and the reviewer and the
# review date-time go into meta_corrections: both in one transaction, so a failure writes neither.
# empty string is null. the date-time is postgres's now(), in the server's time zone
def upsert_corrections(dataset: str, rows: list[dict], reviewer: str) -> None:
    row_ids = [row["row_id"] for row in rows]
    with engine.begin() as connection:
        connection.execute(_corr_upsert(dataset, rows))
        connection.execute(_meta_corr_upsert(row_ids, reviewer))


# the upsert of the rows into corrections, matched by row_id
def _corr_upsert(dataset: str, rows: list[dict]) -> Insert:
    corr = get_corr(dataset)
    values = [{name: row.get(name) or None for name in corr.columns.keys()} for row in rows]
    statement = insert(corr).values(values)
    return statement.on_conflict_do_update(
        index_elements=[corr.c.row_id],
        set_={name: statement.excluded[name] for name in corr.columns.keys() if name != "row_id"},
    )


# the upsert of who reviewed each row, and when, into meta_corrections, matched by row_id and kind
def _meta_corr_upsert(row_ids: list[str], reviewer: str) -> Insert:
    meta = _get_table_from_name("dw_corrections", "meta_corrections")
    review_date_time = func.to_char(func.now(), 'YYYY-MM-DD"T"HH24:MI:SSTZH:TZM')
    values = [
        fact
        for row_id in row_ids
        for fact in (
            {"row_id": row_id, "kind": "meta_reviewed_by", "description": reviewer},
            {"row_id": row_id, "kind": "meta_reviewed_date_time", "description": review_date_time},
        )
    ]
    statement = insert(meta).values(values)
    return statement.on_conflict_do_update(
        index_elements=[meta.c.row_id, meta.c.kind], set_={"description": statement.excluded.description}
    )


# the table of a dataset in each layer: get_corr("journal_entries") is dw_corrections.corr_journal_entries
def get_brnz(dataset: str) -> Table:
    return _get_table_from_name("dw_bronze", f"brnz_{dataset}")


def get_corr(dataset: str) -> Table:
    return _get_table_from_name("dw_corrections", f"corr_{dataset}")


def get_cand(dataset: str) -> Table:
    return _get_table_from_name("dw_candidate", f"cand_{dataset}")


def get_aud(dataset: str) -> Table:
    return _get_table_from_name("dw_audit", f"aud_{dataset}")


# the table is reflected: its columns and their types are read from the database, so a query selects them by name and
# sqlalchemy quotes every name itself. a table that does not exist raises NoSuchTableError naming it
def _get_table_from_name(schema: str, name: str) -> Table:
    return Table(name, MetaData(), schema=schema, autoload_with=engine)

