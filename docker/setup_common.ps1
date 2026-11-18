# what the dev and prod setups share (02_setup_dev.ps1, 03_setup_prod.ps1), written once here: the checks, the start of
# the stack and the setup build. not run by itself: each setup loads it with ". $PSScriptRoot\setup_common.ps1", then
# calls these functions with its own compose arguments ($Compose), from the repo root

# windows powershell 5.1 does not stop on a failed native command, so every docker and git call is checked with Assert-Ok
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

# the env file of the environment, written by 01_setup_env.ps1, and docker answering: before anything else
function Assert-Ready([string]$envFile) {
    if (-not (Test-Path $envFile)) {
        throw "missing: ${envFile}. run: powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1"
    }
    if (-not (Test-Docker version --format '{{.Server.Version}}')) {
        throw 'docker does not answer: open Docker Desktop and wait until the engine runs'
    }
}

# postgres, the airflow database when it is missing, then the rest of the stack
function Start-Warehouse([string[]]$Compose) {
    # postgres alone first: airflow-init needs the airflow database, which the init scripts make only on an empty volume.
    # --wait returns once the healthcheck of docker/compose.yaml passes, which is checked over tcp, so after the init scripts
    Write-Host 'starting postgres'
    & docker @Compose up -d --wait postgres
    Assert-Ok 'starting postgres'

    # a volume from before airflow has no airflow database: made with the same script the init folder runs
    $exists = & docker @Compose exec -T postgres psql -U postgres -d postgres -Atc "select 1 from pg_database where datname = 'airflow'"
    Assert-Ok 'looking for the airflow database'
    if ($exists -ne '1') {
        Write-Host 'creating the airflow database'
        & docker @Compose exec -T postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/00_create_airflow_database.sql
        Assert-Ok 'creating the airflow database'
    }

    # airflow-init first: it migrates the airflow database, installs dev's dbt packages and refreshes airflow's manifest
    # (docker/compose.yaml), then the other airflow services start. up fails when airflow-init does
    Write-Host 'starting airflow and the web apps'
    & docker @Compose up -d
    Assert-Ok 'docker compose up'
}

# dbt's connection, then every relation (the dbt selector setup, DataWarehouseDbt/selectors.yml)
function Invoke-SetupBuild([string[]]$Compose) {
    # the scheduler runs dbt, so its connection is the one that counts
    Write-Host 'checking the dbt connection'
    & docker @Compose exec -T airflow-scheduler dbt debug
    Assert-Ok 'dbt debug'

    # elementary's tables, the seeds and every model, without the data tests of a load, in one dbt build: one dbt
    # process creates each schema once, before any node runs. no load is open, so staging is empty and silver and gold
    # are created empty, or keep what they hold. in the scheduler, which runs dbt for the dags, with its project and
    # packages: the repo's in dev, the release's in prod. its own target and logs, setup-build (x-dbt-env in
    # docker/compose.yaml), so it never writes airflow's manifest. it builds staging, silver and gold, as a load does, so
    # never while a load runs. the variables are the container's: single quotes keep them from powershell, bash expands
    # them
    Write-Host 'building the seeds, every model and elementary'
    & docker @Compose exec -T airflow-scheduler bash -c 'dbt build --selector setup --target-path $DBT_STATE_DIR/setup-build/target --log-path $DBT_STATE_DIR/setup-build/logs'
    Assert-Ok 'dbt build --selector setup'
}
