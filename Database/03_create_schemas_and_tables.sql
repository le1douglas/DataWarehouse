
-- Creates only what dbt does not: the bronze schemas and tables.
-- dbt creates dev_silver, dev_gold, dev_experiments, prod_silver and prod_gold.
 
CREATE SCHEMA dev_bronze;
CREATE SCHEMA prod_bronze;
 
CREATE TABLE dev_bronze.journal_entries (
    date_time              VARCHAR(50),
    subject                VARCHAR(50),
    notes                  VARCHAR(400),   -- free text, can get long
    type                   VARCHAR(50),
    ec                     VARCHAR(50),
    ec_pore                VARCHAR(50),
    ec_bulk                VARCHAR(50),
    ph                     VARCHAR(50),
    mc                     VARCHAR(50),
    temp                   VARCHAR(50),
    device                 VARCHAR(50),
    media                  VARCHAR(50),
    tags                   VARCHAR(50),
    meta_extract_date_time TIMESTAMP    NOT NULL,
    meta_source            VARCHAR(400) NOT NULL -- path, can get long
);

-- create the same table in prod_bronze 
CREATE TABLE prod_bronze.journal_entries (LIKE dev_bronze.journal_entries INCLUDING ALL);
 