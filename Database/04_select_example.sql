SELECT * FROM prod_bronze.journal_entries;
--TRUNCATE prod_bronze.journal_entries
SELECT * FROM dev_bronze.journal_entries;


SELECT * FROM dev_experiments.journal_entries


SELECT * FROM dev_silver.journal_entries;
SELECT * FROM prod_silver.journal_entries;

select * from "DataWarehouse"."dev_experiments"."stg_journal_entries"