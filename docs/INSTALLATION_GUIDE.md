# Installation guide

How to set up the DataWarehouse project on a new Windows PC, from an empty machine to a working repo, database and Excel connection.

You need administrator rights for the PostgreSQL installer, and a GitHub account with access to the repo.

Follow the sections in order, each one needs the ones before it:

1. [Git and repo download](#git-and-repo-download): install Git, clone the repo, create the files that are not in it
2. [Python](#python): install Python, create the virtual environment, install the libraries (dbt included)
3. [PostgreSQL](#postgresql): install the server and the ODBC driver
4. [VS Code](#vs-code): install the editor and its extensions, create the database, set up dbt
5. [Excel connection](#excel-connection): add the ODBC data source and connect Excel to it

This guide was tested with these versions:

- **Python:** 3.14.7
- **PostgreSQL:** 18.6
- **VS Code:** 1.140.0 (user setup)
- **dbt:** Core 1.12.5, postgres plugin 1.11.0

---

## Git and repo download

[Download](https://git-scm.com/install/windows)

**In the installer:**

- **Select component:** all defaults + "Add a Git Bash Profile to Windows Terminal"
- **Default editor:** leave the default, VS Code is not installed yet (it is set in [VS Code](#vs-code))
- **Initial branch name:** master
- **SSH executable:** bundled OpenSSH
- **Line endings:** Checkout Windows-style, commit Unix-style
- **PATH environment:** Git from the command line and also from 3rd-party software
- **HTTPS transport:** Windows Secure Channel
- **Git pull behaviour:** Fast-forward or merge (the default)
- **Credential helper:** Git Credential Manager
- **Extra options:** default
- **Components:** default

**In a new terminal, when finished:**

- `git --version`

### Set username and email

**In a terminal:**

- `git config --global user.name "Your Name"`
- `git config --global user.email "you@example.com"`

### Get the repo from GitHub

**In a terminal:**

- `cd` into the folder where the repo should live
- `git clone https://github.com/le1douglas/DataWarehouse.git`
  - If GitHub asks to sign in, a browser window opens (Git Credential Manager)
- `cd DataWarehouse`
- `git status` (should say "nothing to commit, working tree clean")
- Check if you have history with: `git log --oneline`

### Files you must create manually

They are not included in the repo, but nothing works until each one exists.

| What | Where | Used for | How to get it |
|---|---|---|---|
| `.env` | Repo root | Database credentials for Python | Create the file, paste the sample below, modify it with your credentials. These are the same credentials you will use in Postgres later |
| `journal_entries_corrections.xlsx` | Desktop, outside the repo | The review workbook | TODO Copy it by hand from the other PC, it is not on GitHub |

Sample `.env`, fill it with the password and port from the PostgreSQL installer:

```ini
POSTGRESQL_SERVER=localhost
POSTGRESQL_DB=DataWarehouse
POSTGRESQL_PASSWORD=your-password
POSTGRESQL_USER=postgres
POSTGRESQL_PORT=5432
```

---

## Python

### Install

Windows installer (64-bit) from python.org, under [Downloads](https://www.python.org/downloads/).

**In the installer:**

- "Add python.exe to PATH" ticked
- Install for this user
- Disable path length limit

**In a new PowerShell:**

- `python --version`
- `py --version`
- If python opens the Microsoft Store instead, go to Settings -> Apps -> Advanced app settings -> App execution aliases, and turn off the `python.exe` and `python3.exe` aliases

### Create virtual environment

**In PowerShell:**

- `cd` into the repo
- `python -m venv .venv`
- `.venv\Scripts\Activate.ps1`
  - This might get stopped by PowerShell: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (allow to run locally created scripts and digitally signed ones, apply only to current user)
  - Alternatively, command prompt (`cmd /c`): `.venv\Scripts\activate.bat`
- `python -m pip install --upgrade pip`

### Install libraries

**In PowerShell, inside the venv:**

- `pip install -r requirements.txt`
- `pip install -e ".[dev]"`
- Verify by:
  - `pip check`
  - `pip list`
  - `python -c "import pandas, pydantic, sqlalchemy, psycopg, dotenv; print('ok')"`

---

## PostgreSQL

### Install

[Download version Windows x86-64](https://www.postgresql.org/download/windows/)

**In the installer (run as an administrator):**

- **Installation directory:** default
- **Select:** PostgreSQL server, Stack Builder, command line tools, psqlODBC 64-bit if it's in the list
- **Unselect:** pgAdmin
- Set and write down superuser password
- Write down the port (default is 5432)
- **Locale:** default
- Leave "Launch Stack Builder" ticked

### Stack Builder install of psqlODBC

**In Stack Builder:**

- Select PostgreSQL server
- Categories -> database driver -> psqlodbc
- To function properly it needs to be added to "ODBC Data Sources (64-bit)", this will be done later (look into [Excel connection](#excel-connection))

### Add bin to PATH

**In Windows:**

- Start
- Environment variables
- System variables
- Path
- Edit
- New
- `C:\Program Files\PostgreSQL\18\bin`
- OK/apply on all windows

**In a new PowerShell:**

- `psql --version`
- `Get-Service *postgres*`

To test the connection, i suggest connecting with VS Code, or alternatively `psql -U postgres -h localhost`

---

## VS Code

[Download](https://code.visualstudio.com/)

**In the installer:**

- "Add to PATH" so `code .` works
- Add open with code explorer in context menu

**In a terminal:**

- `git config --global core.editor "code --wait"` (makes VS Code the default editor of Git)
- `cd` into the repo
- `code .`

**In VS Code, when it opens:**

- Do you trust the authors of this folder? Yes
- VS Code should see git as soon as it's in the PATH. Verify in the sidebar
- From the sidebar, extensions (or Ctrl+Shift+X)

### Python (from Microsoft)

Pylance and python debugger should download automatically.

#### Select the interpreter

**In VS Code:**

- Ctrl+Shift+P -> "Python: Select Interpreter" -> `.venv`
- On the bottom right it should show interpreter is `.venv`
- Terminal -> new terminal and verify you are inside venv
- `where.exe python` (the first line should end in `.venv\Scripts\python.exe`)

### PostgreSQL (from Microsoft)

**In the PostgreSQL sidebar:**

- Add connection
  - **Host:** localhost
  - **Port:** 5432
  - **Database:** postgres
  - **User:** postgres
  - **Password:**

**On successful connection:**

- Right click on database -> new query
- `SELECT version();`
- Right click on database -> connect with psql
- `\l` (returns a list of db)
- Run sql: TODO create SQL setup script

### dbt

dbt itself installed through `requirements.txt` (dbt-postgres, dbt-core), in venv.

**In a new terminal, inside the venv:**

- `dbt --version`
- `cd` into `\DataWarehouseDbt` subfolder
- `dbt init` (if done in the same folder as `dbt_project.yml`, this will basically only connect to db and create a dummy `profiles.yml`)
- `dbt debug` (makes sure all yml files are present)
  - Lists convenient link to `profiles.yml` (usually in `%USERPROFILE%\.dbt\profiles.yml`)
- Replace the content of this `profiles.yml` with the sample below, with the password and port from the PostgreSQL installer
- `dbt debug` again (all checks should pass now)
- `dbt deps` (downloads `dbt_utils` into `dbt_packages\`, which is not in the repo)

Sample `profiles.yml`:

```yaml
DataWarehouseDbt:
  target: dev
  outputs:
    dev:
      dbname: DataWarehouse
      host: localhost
      password: your-password
      port: 5432
      schema: dev   # -> dev_silver, dev_gold
      threads: 1
      type: postgres
      user: postgres
```

### dbt Power User

Make sure the interpreter is `.venv` so it can find dbt.

---

## Excel connection

### Add data source

**In Start -> ODBC Data Sources (64-bit):**

- Drivers tab
- Make sure PostgreSQL Unicode(x64) (and ANSI) are installed
- System DSN tab
- Add
- PostgreSQL Unicode(x64)
- Fill the dialog
  - **Data source name:** `PostgreSQL_DataWarehouse`
  - **Database:** `DataWarehouse`
  - **Server:** localhost
  - **User Name:** postgres (TODO change to read only user)
  - **Description:** empty
  - **SSL Mode:** disable
  - **Port:** 5432 (or whatever it is)
  - **Password:** \*\*\*\*\*\* (stored in the registry in readable form, for a read only user, not a problem)
- Test (Connection successful)
- Save

### Connect from Excel

**In Excel:**

- Get data
  - From other sources
  - From ODBC
- **Data source name:** whatever was used in previous step
- Database side bar
  - **User name:** postgres (TODO change to read only user)
  - **Password:** \*\*\*\*\*
- From the navigator
  - Select a table
  - Load to or transform

If you ever want to change this setting: get data -> data source settings
