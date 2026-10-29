# dev setup: starts postgres, builds the dbt, loader and webapps images, installs the dbt packages and checks dbt's connection.
# safe to run again: up and build change only what changed, dbt deps reinstalls the same versions.
# loads nothing: the bronze load appends, so it stays a step of its own (see docs/INSTALLATION_GUIDE_DOCKER.md)
# needs the env files (01_setup_env.ps1) and Docker Desktop running. from the repo root:
#   powershell -ExecutionPolicy Bypass -File docker\02_setup_dev.ps1
$ErrorActionPreference = 'Stop'

# windows powershell 5.1 does not stop on a failed native command, so every docker call is checked with Assert-Ok
function Assert-Ok([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit code $LASTEXITCODE)" }
}

# true when the docker command succeeds, its output hidden. Continue only inside this function: with Stop, powershell
# 5.1 turns a redirected stderr line of a native command into an error that ends the script
function Test-Docker {
    $ErrorActionPreference = 'Continue'
    & docker @args 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
}

$dev = @("compose", "-f", "docker/compose.yaml", "-f", "docker/compose.dev.yaml")

# the paths below are from the repo root (the compose files and env files are in docker/)
Push-Location (Resolve-Path "$PSScriptRoot\..")
try {
    $missing = @('.env', '.env.loader', '.env.transformer', '.env.webapps' | Where-Object { -not (Test-Path "docker\$_") })
    if ($missing.Count -gt 0) {
        throw "missing in docker\: $($missing -join ', '). run: powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1"
    }

    if (-not (Test-Docker version --format '{{.Server.Version}}')) { throw 'docker does not answer: open Docker Desktop and wait until the engine runs' }

    Write-Host 'starting postgres'
    & docker @dev up -d
    Assert-Ok 'docker compose up'

    # over tcp: during the first start the init scripts run on a server that listens on the socket only, so a plain
    # pg_isready would answer before the DDL is done
    Write-Host 'waiting for postgres'
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-Docker @dev exec -T postgres pg_isready -h localhost -U postgres) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw 'postgres is not ready after 2 minutes: see the logs of dw-dev-postgres-1 in Docker Desktop' }

    Write-Host 'building the dbt, loader and webapps images'
    & docker @dev build dbt loader webapps
    Assert-Ok 'the build'

    # the repo mount hides the packages installed in the image, so dev keeps its own in DataWarehouseDbt/dbt_packages
    Write-Host 'installing the dbt packages'
    & docker @dev run --rm dbt deps
    Assert-Ok 'dbt deps'

    Write-Host 'checking the dbt connection'
    & docker @dev run --rm dbt debug
    Assert-Ok 'dbt debug'

    Write-Host 'dev setup done. next: docker compose -f docker/compose.yaml -f docker/compose.dev.yaml run --rm loader bronze'
}
finally {
    Pop-Location
}
