# creates the six env files of dev and prod in this folder, next to compose.yaml
# when some exist, one question: yes overwrites them all, no keeps them and creates only the missing ones
# asks for the postgres password of each environment, only when its project env file (.env or .env.prod) is written
# the input folders are hardcoded: temporary locations until the day-to-day ones are decided
# run from Windows: powershell -ExecutionPolicy Bypass -File docker\create_env_files.ps1
$ErrorActionPreference = 'Stop'

function Read-Password([string]$environment) {
    while ($true) {
        $first = Read-Host -AsSecureString "postgres password for $environment"
        $second = Read-Host -AsSecureString "again"
        $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($first))
        $repeated = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($second))
        # compose reads the env file as is: no quotes, so no spaces, and $ and # would be read as a variable or a comment
        if ($password -ne $repeated) { Write-Host 'the two passwords differ'; continue }
        if ($password -eq '') { Write-Host 'the password is empty'; continue }
        if ($password -match '[\s$#"'']') { Write-Host 'no spaces, quotes, $ or # in the password'; continue }
        return $password
    }
}

# the newest git tag, by creation date: the release prod runs. windows powershell 5.1 does not stop on a failed
# native command, so the exit code is checked. every tag is read first: Select-Object -First 1 in the pipe would stop
# git early and leave a failed exit code
function Get-LatestRelease {
    $tags = @(git -C $PSScriptRoot tag --sort=-creatordate)
    if ($LASTEXITCODE -ne 0 -or $tags.Count -eq 0) { throw 'no git tag found: run git fetch --tags, then this script again' }
    return $tags[0]
}

$names = '.env', '.env.prod', '.env.loader', '.env.prod.loader', '.env.transformer', '.env.prod.transformer'
$existing = @($names | Where-Object { Test-Path (Join-Path $PSScriptRoot $_) })
$overwrite = $false
if ($existing.Count -gt 0) {
    Write-Host "these exist: $($existing -join ', ')"
    $overwrite = (Read-Host 'overwrite them all? [y/N]') -eq 'y'
}

# true when the file is missing, or the user answered y. anything else keeps the file
function Confirm-Write([string]$name) {
    if ($overwrite -or ($existing -notcontains $name)) { return $true }
    Write-Host "skipped  $name"
    return $false
}

# utf-8 without BOM and LF line endings: a BOM would become part of the first variable name
function Save-EnvFile([string]$name, [string]$content) {
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot $name), ($content -replace "`r`n", "`n"), (New-Object Text.UTF8Encoding $false))
    Write-Host "written  $name"
}

function Write-EnvFile([string]$name, [string]$content) {
    if (Confirm-Write $name) { Save-EnvFile $name $content }
}

if (Confirm-Write '.env') {
    $devPassword = Read-Password 'dev'
    Save-EnvFile '.env' @"
# the dev compose env file. not in git. compose reads it by itself from this folder, the folder of compose.yaml (and so do the Dev Containers), no --env-file needed
POSTGRES_DB=DataWarehouse
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$devPassword
POSTGRES_PORT=5432
RELEASE=dev
# windows folders mounted read only into the loader container. each can move: change the line, no rebuild needed
# the root of the csv exports, mounted at /inbox/exports. SampleData until the day-to-day location is decided
EXPORTS_DIR=../SampleData
# the folder of the corrections workbook, mounted at /inbox/corrections. the dev workbook, not in git
CORRECTIONS_DIR=../user_input/corrections_dev
# windows folder mounted into the datastreamer container, at /daily_raw_csv: where the csv of a part of the day is saved
# TODO placeholder (2026-10-22): align with the .env on the other machine
DAILY_RAW_CSV_DIR=../user_input/journal_entries

"@
}

if (Confirm-Write '.env.prod') {
    $prodPassword = Read-Password 'prod'
    $release = Get-LatestRelease
    Save-EnvFile '.env.prod' @"
# the prod compose env file. not in git. pass it explicitly: --env-file docker/.env.prod
POSTGRES_DB=DataWarehouse
POSTGRES_USER=postgres
# only applied when the pgdata volume is created. changing it later needs ALTER USER in the database as well
POSTGRES_PASSWORD=$prodPassword
# published to Windows: dev is on 5432
POSTGRES_PORT=5433
# the git tag, the same name: the newest tag when this file was written. prod does not start before that image exists
RELEASE=$release
# windows folders mounted read only into the loader container
# TODO placeholder (2026-10-22): the same folder as dev until the day-to-day location is decided
EXPORTS_DIR=../SampleData
# the prod corrections workbook, in git and released with each tag
CORRECTIONS_DIR=../user_input/corrections_prod
# windows folder mounted into the datastreamer container, at /daily_raw_csv
# TODO placeholder (2026-10-22): compose.yaml requires it even though prod does not run the datastreamer yet
DAILY_RAW_CSV_DIR=../user_input/journal_entries

"@
}

Write-EnvFile '.env.loader' @'
# connection and inputs for the loader container, read by src/datawarehouse/config.py. not in git
# host is the postgres service name in compose.yaml: containers of one compose project reach each other by service name
POSTGRESQL_SERVER=postgres
# the port inside the docker network, where the postgres container always listens (5432).
# not POSTGRES_PORT from .env, which is the port published to Windows and changes per environment
POSTGRESQL_PORT=5432
# the database, user and password come from POSTGRES_DB, POSTGRES_USER and POSTGRES_PASSWORD in the project
# env file (.env or .env.prod), set in compose.yaml: written once per environment
# each input file, relative to its mounted folder: /inbox/exports (EXPORTS_DIR) and /inbox/corrections (CORRECTIONS_DIR)
JOURNAL_ENTRIES_CSV=drip_drain_csv/journal-entries.csv
CORRECTIONS_WORKBOOK=journal_entries_corrections.xlsx

'@

Write-EnvFile '.env.prod.loader' @'
# connection and inputs for the prod loader container, read by src/datawarehouse/config.py. not in git
# host is the postgres service name in compose.yaml: containers of one compose project reach each other by service name
POSTGRESQL_SERVER=postgres
# the port inside the docker network, where the postgres container always listens (5432).
# not POSTGRES_PORT from .env.prod, which is the port published to Windows
POSTGRESQL_PORT=5432
# the database, user and password come from POSTGRES_DB, POSTGRES_USER and POSTGRES_PASSWORD in the project
# env file (.env or .env.prod), set in compose.yaml: written once per environment
# each input file, relative to its mounted folder: /inbox/exports (EXPORTS_DIR) and /inbox/corrections (CORRECTIONS_DIR)
JOURNAL_ENTRIES_CSV=drip_drain_csv/journal-entries.csv
CORRECTIONS_WORKBOOK=journal_entries_corrections.xlsx

'@

Write-EnvFile '.env.transformer' @'
# connection for the dbt container, read by DataWarehouseDbt/profiles.yml. not in git
# host is the postgres service name in compose.yaml: containers of one compose project reach each other by service name
DBT_HOST=postgres
# the port inside the docker network, where the postgres container always listens (5432).
# not POSTGRES_PORT from .env, which is the port published to Windows and changes per environment
DBT_PORT=5432
# the database, user and password come from POSTGRES_DB, POSTGRES_USER and POSTGRES_PASSWORD in the project
# env file (.env or .env.prod), set in compose.yaml: written once per environment

'@

Write-EnvFile '.env.prod.transformer' @'
# connection for the prod dbt container, read by DataWarehouseDbt/profiles.yml. not in git
# host is the postgres service name in compose.yaml: containers of one compose project reach each other by service name
DBT_HOST=postgres
# the port inside the docker network, where the postgres container always listens (5432).
# not POSTGRES_PORT from .env.prod, which is the port published to Windows
DBT_PORT=5432
# the database, user and password come from POSTGRES_DB, POSTGRES_USER and POSTGRES_PASSWORD in the project
# env file (.env or .env.prod), set in compose.yaml: written once per environment

'@
