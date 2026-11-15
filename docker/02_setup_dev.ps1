# dev setup: builds the airflow, webapps and dev images, starts postgres, creates the airflow database when it is missing,
# starts airflow and the web apps, installs the dbt packages and the meltano plugins and checks dbt's connection.
# safe to run again: up and build change only what changed, the airflow database is created only once, dbt deps and
# meltano install reinstall the same versions.
# loads nothing: the bronze load appends, so it stays a step of its own (see docs/INSTALLATION_GUIDE_DOCKER.md)
# needs the env file (01_setup_env.ps1) and Docker Desktop running. from the repo root:
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
    if (-not (Test-Path 'docker\.env')) {
        throw 'missing: docker\.env. run: powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1'
    }

    if (-not (Test-Docker version --format '{{.Server.Version}}')) { throw 'docker does not answer: open Docker Desktop and wait until the engine runs' }

    # before up, so up starts the services on the new images, not on the ones of the last build. the airflow services
    # share one image: building airflow-init builds it for all of them
    Write-Host 'building the airflow, webapps and dev images'
    & docker @dev --profile dev build airflow-init webapps dev
    Assert-Ok 'the build'

    # postgres alone first: airflow-init needs the airflow database, which the init scripts make only on an empty volume.
    # --wait returns once the healthcheck of docker/compose.yaml passes, which is checked over tcp, so after the init scripts
    Write-Host 'starting postgres'
    & docker @dev up -d --wait postgres
    Assert-Ok 'starting postgres'

    # a volume from before airflow has no airflow database: made with the same script the init folder runs
    $exists = & docker @dev exec -T postgres psql -U postgres -d postgres -Atc "select 1 from pg_database where datname = 'airflow'"
    Assert-Ok 'looking for the airflow database'
    if ($exists -ne '1') {
        Write-Host 'creating the airflow database'
        & docker @dev exec -T postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/00_create_airflow_database.sql
        Assert-Ok 'creating the airflow database'
    }

    # airflow-init migrates the airflow database first, then the other airflow services start
    Write-Host 'starting airflow and the web apps'
    & docker @dev up -d
    Assert-Ok 'docker compose up'

    # the repo mount hides the packages installed in the image, so dev keeps its own in the dbt-state volume
    # (docker/compose.dev.yaml), shared by the scheduler, which runs dbt, and the dev container
    Write-Host 'installing the dbt packages'
    & docker @dev exec -T airflow-scheduler dbt deps
    Assert-Ok 'dbt deps'

    # the same for meltano: dev keeps its own plugins in the meltano-plugins volume (docker/compose.dev.yaml)
    Write-Host 'installing the meltano plugins'
    & docker @dev exec -T airflow-scheduler meltano install
    Assert-Ok 'meltano install'

    Write-Host 'checking the dbt connection'
    & docker @dev exec -T airflow-scheduler dbt debug
    Assert-Ok 'dbt debug'

    Write-Host 'dev setup done. next: a load (meltano run tap-csv-<dataset> target-postgres, then its dbt build), see docs/INSTALLATION_GUIDE_DOCKER.md'
}
finally {
    Pop-Location
}
