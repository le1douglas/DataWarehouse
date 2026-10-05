
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
demical separator is --> . (23.5 is 23 and a half)

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




## SETUP

------------------
execute 02_create database //TODO CREATE A SETUP SCRIPT

run
psql -U postgres -h localhost -d DataWarehouse -1 -v ON_ERROR_STOP=1 -f Database\03_create_schemas_and_tables.sql
from root of the repo.
----------------------




##### **from home:**

copy whole root repo, including .env. excluding .venv, \_\_pychache\_\_ and DataWarehouseDbt/target





copy profiles.yml from %USERPROFILE%\\.dbt\\





##### **at work:**

paste whole root repo folder

(including .env) //check if port is correct after installing postgres





##### **Python 3.14.7**



**Install**

Windows installer (64-bit) from python.org, under [Downloads](https://www.python.org/downloads/).

on installer:

* "Add python.exe to PATH" ticked
* install for this user
* Disable path length limit

new powershell

* python --version
* py --version
* if python opens the Microsoft Store instead, go to Settings, Apps, Advanced app settings, App execution aliases, and turn off the python.exe and python3.exe aliases.



**Create virtual enviroment**

powershell

* cd In the repo
* python -m venv .venv
* .venv\\Scripts\\Activate.ps1
* ^ this might get stopped by powershell.
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned.
allow to run locally created scripts and digitally signed ones. apply only to current user.
* alternatevly, command prompt (cmd /c) .venv\\Scripts\\activate.bat
* python -m pip install --upgrade pip





**install libraries**

make sure you are in venv

* pip install -r requirements.txt
* pip install -e ".\[dev]"
* verify by

  * pip check
  * pip list
  * python -c "import pandas, pydantic, sqlalchemy, psycopg, dotenv; print('ok')"





##### **Postgres 18.6**



**install**

[download version 18.6 - Windows x86-64](https://www.postgresql.org/download/windows/)

run installer as an administrator

* installation directory (default)
* select: PostgreSQL server, stack builder, command lines tool, psqlODBC 64-bit if its in the list
* unselect: pgAdmin
* set and write down superuser password
* write down the port (5432?)
* default locale
* leave "Launch Stack Builder" ticked.



**stackbuiler install of psqlODBC**

stackbuiler

* select postgres server
* categries - > database driver -> psqlodbc
* add to "ODBC Data Sources (64-bit)" look into excel connection





**add bin to path**

* start
* environments variables
* user variables (or system variables?)
* path
* edit
* new
* C:\\Program Files\\PostgreSQL\\18\\bin
* ok/apply on all windows

new power shell

* psql --version
* Get-Service \*postgres\*



Actually connect with vs code, or alternatively psql -U postgres -h localhost













##### **VS Code 1.140.0 (user setup)**

[Download](https://code.visualstudio.com/),

from the installer

* "Add to PATH" so "code ."  works
* add open with code explorer in context menu

open terminal

* cd into the repo
* code .

when vscode opens

* Do you trust the authors of this folder? yes
* from the sidebar, extensions (or cntl shift x)



###### **Python** (from Microsoft)

Pylance and python debugger should download automatically.



**Select the interpreter:**

* Ctrl+Shift+P, "Python: Select Interpreter", then .venv
* on the bottom right it should see interpreter is .venv
* terminal -> new terminal and verify you are inside venv
* where.exe python  (The first line should end in .venv\\Scripts\\python.exe)





###### **PostgreSQL** (from Microsoft)

open PostgreSQL in the sidebar

* add connection
* host localhost
* port: 5432
* database: postgres
* user: postgres
* password:

on successful connection:

* right click on database-> new query
* SELECT version();
* right click on database -> connect with psql
* \\l (returns a list of db)
* run sql Create the database, schemas, users etc.







###### **dbt**

dbt itself installed through requirements.txt (dbt-postgres, dbt-core), in venv.

* open new terminal in .venv
* dbt --version. Core: 1.12.5. plugin: postgres: 1.11.0
* cd into \\DataWarehouseDbt subfolder
* dbt init (if done in the same folder as dbt\_project.yml, this will basically only connect to db and create a dummy profiles.yml)
* dbt debug (maeks sure all yml file are present)

&#x20;        lists convenient link to profiles.yml (usually in %USERPROFILE%\\.dbt\\profiles.yml)

* copy content of home profiles.yml to this profiles.yml



###### **dbt Power User**

make sure the interpreter is .venv so it can can find dbt









##### **Git**

[download](https://git-scm.com/install/windows)

on the installer

* select component: all defaults + "Add a Git Bash Profile to Windows Terminal"
* default editor: vs code
* initial branch name: master
* ssh executable: bundled OpenSSH
* Line endings: Checkout Windows-style, commit Unix-style
* PATH environment: Git from the command line and also from 3rd-party software
* HTTPS transport: Windows Secure Channel
* git pull behaviour: Fast-forward or merge (the default)
* Credential helper: Git Credential Manager
* Extra options: default
* Components: default

when finished open new terminal -> git --version



**set username and email**

* git config --global user.name "Your Name"
* git config --global user.email "you@example.com"




**get the folder repo**

* cd in the folder
* git status
* if gives dubious ownership" error: git config --global --add safe.directory C:/Users/path/to/folder/
* check if you have history with: git log --oneline
* git status make sure .venv is not committed.
* **…**
* vs code should see git as soon as it's in the PATH. repoen vs code and verify in the sidebar







##### **Excel connection**

**add data source**

start -> ODBC Data Sources (64-bit)

* drivers tab
* make sure PostgreSQL Unicode(x64) (and ANSI) are installed
* system DSN tab
* add
* PostgreSQL Unicode(x64)
* fill the dialog

  * data source name: PostgreSQL\_DataWarehouse
  * Database: DataWarehouse
  * Server: localhost
  * User Name: postgres  //maybe change to read only user
  * Description: empty
  * SSL Mode: disable
  * Port: 5432 //or whatever it is
  * Password: \*\*\*\*\*\* //	Stored in the registry in readable form, for a read only user, not a problem
* test (Connection successful)
* save





**connect from excel**

* get data

  * from other sources
  * from odcb
* Data source name: whatever was used in previous step.
* Database side bar

  * user name: postgres  //maybe change to read only user
  * password: \*\*\*\*\*
* from the navigator

  * select a table
  * load to or transform



if you ever want to change this setting, get data-> data source settings









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

