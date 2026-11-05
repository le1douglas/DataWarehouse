
# DataWarehouse

Data warehouse, medallion architecture (raw bronze, cleaned silver, business ready gold)

The design goal is that bad data never reaches silver: a file that fails its data tests is refused, and it is fixed where it came from.

## Regual DB maintenance
# Index maintenance
todo find out how index maintance works in posgresql
https://wiki.postgresql.org/wiki/Index_Maintenance

monitor index usage 
monitor index duplication
monitor fragmentation
- lesstha 10% no action
- 10-30% reorganize
- more than 30 rebuild

# Storage use
monitor over all db size
monitor table size
change vacuum defaults?


## Backup and restore strategy
find uptime requirements
find data loss tolerance



## Role	Permissions
todo decide on the roles to use
postgres ---> superuser responsable for permissions and owns bronze layer
extract_load_user	----> Meltano (target-postgres)	INSERT and SELECT on bronze
transform_user	---> what dbt connects as.	owns the  silver/gold schemas, with CREATE on the database, only select needed in bronze
read_only_user	-----> Excel, Power BI, Tableau, Grafana	USAGE on gold, SELECT on gold, nothing on bronze or silver



this is a hotfix
