# dev setup: builds the pipeline, webapps and dev images, starts postgres, creates the airflow database when it is missing,
# starts airflow and the web apps (airflow-init installs the dbt packages and refreshes airflow's manifest), installs
# the meltano plugins, checks dbt's connection and builds everything no load builds (the dbt selector setup,
# DataWarehouseDbt/selectors.yml).
# safe to run again: up and build change only what changed, the airflow database is created only once, dbt deps and
# meltano install reinstall the same versions, airflow's manifest is refreshed, and the setup build rebuilds the seeds,
# the ref_ models and the dims over them: run it again after one of them changes. not while a load runs: up refreshes
# airflow's manifest, and can recreate the scheduler.
# loads nothing: a load dag, in the airflow ui (see docs/INSTALLATION_GUIDE_DOCKER.md)
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
    Write-Host 'building the pipeline, webapps and dev images'
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

    # airflow-init first: it migrates the airflow database, installs dev's dbt packages and refreshes airflow's manifest
    # (docker/compose.yaml), then the other airflow services start. up fails when airflow-init does
    Write-Host 'starting airflow and the web apps'
    & docker @dev up -d
    Assert-Ok 'docker compose up'

    # the same for meltano: dev keeps its own plugins in the meltano-plugins volume (docker/compose.dev.yaml)
    Write-Host 'installing the meltano plugins'
    & docker @dev exec -T airflow-scheduler meltano install
    Assert-Ok 'meltano install'

    Write-Host 'checking the dbt connection'
    & docker @dev exec -T airflow-scheduler dbt debug
    Assert-Ok 'dbt debug'

    # elementary's tables, the seeds, the ref_ models and the dims over them, in one dbt build: one dbt process creates
    # each schema once, before any node runs. in the scheduler, which runs dbt for the dags, with the same packages. its
    # own target and logs, setup-build (x-dbt-env in docker/compose.yaml), so it never writes airflow's manifest. a
    # load's publish never builds these nodes, so the two can run at once: postgres makes a reader wait. the variables
    # are the container's: single quotes keep them from powershell, bash expands them
    Write-Host 'building the seeds, the ref_ models, the dims and elementary'
    & docker @dev exec -T airflow-scheduler bash -c 'dbt build --selector setup --target-path $DBT_STATE_DIR/setup-build/target --log-path $DBT_STATE_DIR/setup-build/logs'
    Assert-Ok 'dbt build --selector setup'

    Write-Host 'dev setup done. next: a load dag, in the airflow ui (see docs/INSTALLATION_GUIDE_DOCKER.md)'
}
finally {
    Pop-Location
}
