
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


mess around in `experiments`, implement in dev, run in production once dev works.
`prod` cannot `ref()` a model in `experiments` (parse error).

1. Create `my_model.sql` in `models/experiments/`
2. `dbt build --select path:models/experiments`
3. Move (not copy) `my_model.sql` to `models/bronze_to_silver/`
4. (Optional) `dbt build --select my_model+`
   Rebuilds my_model and everything downstream. The trailing `+` matters: Gold views
   stay linked to the old version of the Silver table unless they are rebuilt too.
5. `dbt build` builds in dev. Fails if any experiment errors; use
   `dbt build --exclude path:models/experiments` if that gets annoying.
6. `dbt parse --target prod` parses in prod.
   A model that `ref()`s an experiment builds fine in dev and only breaks in
   prod. This writes nothing and catches it.
7. `dbt build --target prod` finally, build in prod


is still your responsability to:
- create dev_bronze and prod_bronze schemas and tables
- make sure dev_bronze is representative of prod_bronze
- make sure python loads into prod_bronze (and then copy in dev_bronze with sql so they are synced?)
- clean up inside dev_experiments
- delete or otherwise make a decision about orphan tables



|model in Folder...| ...sources from (dev)... |...builds into schema (dev)| ...sources from (prod)... |...build into schema (prod)|
|------------------|--------------------------|---------------------------|---------------------------|---------------------------|
|experiments|dev_bronze, dev_silver, dev_gold|dev_experiments|cannot build|cannot build|
|bronze_to_silver|dev_bronze|dev_silver|prod_bronze|prod_silver|
|silver_to_gold|dev_silver|dev_gold|prod_silver|prod_gold|


## Regual DB maintenance

**index management**
monitor index usage //this resets after every bootwhen running locally?
monitor potential index to add //this resets after every bootwhen running locally?
montor duplicate indexes
update statistics 
monitor fragmentation
- lesstha 10% no action
- 10-30% reorganize
- more than 30 rebuild

