
# DataWarehouse

TODO define architecture

## EXTERNAL TO BRONZE

Python
- pandas -> workhorse of in memory data manipulation
- pydantic -> define and validate
- sqlalchemy -> talking to datatabase (no ORM schema definition)
- ...
- pytest -> testing
- ~~pyspark -> for distributed systems, not necessary for now~~

empty strings "" are to be trated as null
timezones are to be interptreted as UTC amsterdam even when not specified.

## BRONZE TO SILVER
- SQL stored procedures
- dbt
- Excel manual review
- Python manual review

## SILVER TO GOLD
- SQL stored procedures
- dbt?


## GOLD TO USER
- power bi
- tableau
- grafana

TODO for deployment  check
pytest --cov=. --cov-report=html
start htmlcov/index.html



sync or think amout .toml instead of requirements.txt
pip install -e ".[dev]"
pip freeze --exclude-editable > requirements.txt
