# creates the env files .env (dev) and .env.prod next to compose.yaml
# - when some exist, one question: yes overwrites them all, no creates only the missing ones
# - the input and output folders are temporary, until the day-to-day ones are decided
# run from Windows: powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1
$ErrorActionPreference = 'Stop'

function Read-Password([string]$environment) {
    while ($true) {
        $first = Read-Host -AsSecureString "postgres password for $environment"
        $second = Read-Host -AsSecureString "again"
        $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($first))
        $repeated = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($second))
        if ($password -ne $repeated) { Write-Host 'the two passwords differ'; continue }
        if ($password -eq '') { Write-Host 'the password is empty'; continue }
        # compose reads the env file as is: no quotes, so no spaces, and $ and # would be read as a variable or a comment
        if ($password -match '[\s$#"'']') { Write-Host 'no spaces, quotes, $ or # in the password'; continue }
        return $password
    }
}

# hex: safe in an env file, which compose reads as is
function New-Secret {
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

# the newest git tag: the release prod runs
# - powershell 5.1 does not stop on a failed native command, so the exit code is checked
# - every tag is read first: Select-Object -First 1 would stop git early, with a failed exit code
function Get-LatestRelease {
    $tags = @(git -C $PSScriptRoot tag --sort=-creatordate)
    if ($LASTEXITCODE -ne 0 -or $tags.Count -eq 0) { throw 'no git tag found: run git fetch --tags, then this script again' }
    return $tags[0]
}

$names = '.env', '.env.prod'
$existing = @($names | Where-Object { Test-Path (Join-Path $PSScriptRoot $_) })
$overwrite = $false
if ($existing.Count -gt 0) {
    Write-Host "these exist: $($existing -join ', ')"
    $overwrite = (Read-Host 'overwrite them all? [y/N]') -eq 'y'
}

function Confirm-Write([string]$name) {
    if ($overwrite -or ($existing -notcontains $name)) { return $true }
    Write-Host "skipped  $name"
    return $false
}

# utf-8 without BOM: a BOM would become part of the first variable name
function Save-EnvFile([string]$name, [string]$content) {
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot $name), ($content -replace "`r`n", "`n"), (New-Object Text.UTF8Encoding $false))
    Write-Host "written  $name"
}

if (Confirm-Write '.env') {
    $devPassword = Read-Password 'dev'
    Save-EnvFile '.env' @"
# dev's env file, not in git. compose finds it next to compose.yaml, with no --env-file
POSTGRES_DB=DataWarehouse
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$devPassword
POSTGRES_PORT=5432
NICEGUI_PORT=8080
# airflow's page, on localhost only. prod is on 8091
AIRFLOW_PORT=8090
# the key the airflow components sign each other's tokens with
AIRFLOW_JWT_SECRET=$(New-Secret)
RELEASE=dev
# every csv to load, one subfolder per dataset. to move it, change the line and recreate the containers
# - dev's own: neither environment's folder is inside the other's
USER_INPUT_DIR=../user_input_dev
# every file the programs write for the user, one subfolder per program. dev's own
USER_OUTPUT_DIR=../user_output_dev

"@
}

if (Confirm-Write '.env.prod') {
    $prodPassword = Read-Password 'prod'
    $release = Get-LatestRelease
    Save-EnvFile '.env.prod' @"
# prod's env file, not in git. pass it explicitly: --env-file docker/.env.prod
POSTGRES_DB=DataWarehouse
POSTGRES_USER=postgres
# applied only when the pgdata volume is created: changing it later also needs ALTER USER
POSTGRES_PASSWORD=$prodPassword
# dev is on 5432
POSTGRES_PORT=5433
# dev is on 8080
NICEGUI_PORT=8081
# airflow's page, on localhost only. dev is on 8090
AIRFLOW_PORT=8091
# the key the airflow components sign each other's tokens with
AIRFLOW_JWT_SECRET=$(New-Secret)
# the git tag, the newest when this file was written. prod does not start before its image exists
RELEASE=$release
# every csv to load, one subfolder per dataset. prod's own: neither environment's folder is inside the other's
USER_INPUT_DIR=../user_input_prod
# every file the programs write for the user, one subfolder per program. prod's own
USER_OUTPUT_DIR=../user_output_prod

"@
}
