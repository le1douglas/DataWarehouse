
# DataWarehouse

Data warehouse, medallion architecture (raw bronze, cleaned silver, business ready gold)

The design goal is that bad data never reaches silver, and that a non technical user can fix it without touching the source file or the database directly.

## Architecture

For a compelte overview of the data pipeline, see also: [DATA-FLOW.md](docs/DATA-FLOW.md)

| Stage | Status | Done with |
|---|---|---|
| [External to bronze](#external-to-bronze) | Built | Python |
| [Bronze to silver](#bronze-to-silver) | Built | dbt, Excel manual review, Python |
| [Silver to gold](#silver-to-gold) | Planned | Not decided |
| [Gold to user](#gold-to-user) | Planned | Not decided |

Only a `dev` environment exists, so every schema starts with `dev_`. TODO A prod target will be added later.

### External to bronze

Python (`src/datawarehouse`) reads an external source (CSV File, API etc.), validates that each row can be parsed and appends it to `dev_bronze`. No other validation is done. Bronze stores everything as text, exactly as received.

- pandas -> reading the file and in memory data manipulation
- pydantic -> define and validate each row
- sqlalchemy -> talking to the database (no ORM schema definition)
- pytest -> testing

### Bronze to silver

dbt (`DataWarehouseDbt`) builds every layer between bronze and silver, and never changes bronze or corrections.

| Layer | Schema | What it does |
|---|---|---|
| Bronze | `dev_bronze` | Input. Raw data as text, loaded by Python |
| Staging | `dev_staging` | View. Casts the text to types; a value that cannot be cast becomes null and is reported |
| Corrections | `dev_corrections` | Input. Rows fixed by a human, loaded by Python from the Excel workbook |
| Candidate | `dev_candidate` | View. Staging with the corrections applied, plus the derived columns. This is the proposal for silver|
| Audit | `dev_audit` | One failure table per data test, and a view that aggregates these tables per dataset |
| Silver | `dev_silver` | Table. The published result, as in, candidates that passed all the tests |

- **The gate:** `dbt build` runs the data tests on candidate and skips silver when any fails, so silver keeps its last good data.
- **Excel manual review:** the workbook reads candidate and the audit view through ODBC, the reviewer fixes the flagged rows, and Python loads the `corrected` sheet into corrections.
- **A correction replaces the whole row.** Corrections stay in their table and are re-applied on every build.

A full loop is: DDL, load bronze, `dbt build` (tests fail, silver skipped), review in Excel, load corrections, `dbt build` (tests succeed, silver built).

### Data rules

- Empty strings "" are treated as null.
- The decimal separator is `.` (23.5 is 23 and a half). Staging turns a decimal comma into a dot.
- Datetimes have no time zone before silver, and are cut to the second. Silver assigns them to `Europe/Amsterdam`.

### Silver to gold

Not built. Idea so far:

- views over silver. tables ready for reporting software

### Gold to user

Not built. Candidates:

- power bi
- tableau
- grafana




## Documentation

| Document | What it is for |
|---|---|
| [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md) | Setting up a new Windows PC: from scratch to operational |
| [docs/DATA-FLOW.md](docs/DATA-FLOW.md) | Diagram of how data moves from collection to gold, including corrections|
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | The terms used for domain concepts |
| [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Naming conventions, layer prefixes, SQL and Python style guide|
| [CLAUDE.md](CLAUDE.md) | Context and instructions for calude code |
| [docs/agents/](docs/agents/) | Instructions for AI agents: the issue tracker and the domain docs |




_________




TODO for deployment  check
pytest --cov=. --cov-report=html
start htmlcov/index.html



sync or think about .toml instead of requirements.txt
pip install -e ".[dev]"
pip freeze --exclude-editable > requirements.txt




## Regual DB maintenance

**index maintance**
todo find out how index maintance works in posgresql
https://wiki.postgresql.org/wiki/Index_Maintenance

monitor index usage 
monitor index duplication
monitor fragmentation
- lesstha 10% no action
- 10-30% reorganize
- more than 30 rebuild


## Role	Permissions
todo decide on the roles to use
postgres ---> superuser responsable for permissions and owns bronze layer
extract_load_user	----> the Python load script	INSERT on bronze and correction tables
transform_user	---> what dbt connects as.	owns the  silver/gold schemas, with CREATE on the database, only select needed in bronze and corrections
read_only_user	-----> Excel, Power BI, Tableau, Grafana	USAGE on gold, SELECT on gold, nothing on bronze or silver