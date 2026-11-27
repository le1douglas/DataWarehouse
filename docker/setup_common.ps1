# the steps the dev and prod setups share. not run by itself: each setup loads it, then calls these functions with
# its own compose arguments, from the repo root

# powershell 5.1 does not stop on a failed native command, so every docker and git call is checked
function Assert-Ok([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit code $LASTEXITCODE)" }
}

# Continue only inside this function: with Stop, powershell 5.1 turns a redirected stderr line of a native command
# into an error that ends the script
function Test-Docker {
    $ErrorActionPreference = 'Continue'
    & docker @args 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
}

function Assert-Ready([string]$envFile) {
    if (-not (Test-Path $envFile)) {
        throw "missing: ${envFile}. run: powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1"
    }
    if (-not (Test-Docker version --format '{{.Server.Version}}')) {
        throw 'docker does not answer: open Docker Desktop and wait until the engine runs'
    }
}

function Start-Warehouse([string[]]$Compose) {
    # postgres alone first: airflow-init needs the airflow database, which the init scripts make only on an empty volume
    # - --wait returns after the init scripts: the healthcheck is over tcp
    Write-Host 'starting postgres'
    & docker @Compose up -d --wait postgres
    Assert-Ok 'starting postgres'

    # a volume from before airflow has no airflow database
    $exists = & docker @Compose exec -T postgres psql -U postgres -d postgres -Atc "select 1 from pg_database where datname = 'airflow'"
    Assert-Ok 'looking for the airflow database'
    if ($exists -ne '1') {
        Write-Host 'creating the airflow database'
        & docker @Compose exec -T postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/00_create_airflow_database.sql
        Assert-Ok 'creating the airflow database'
    }

    # the other airflow services wait for airflow-init, and up fails when it does
    Write-Host 'starting airflow and the web apps'
    & docker @Compose up -d
    Assert-Ok 'docker compose up'
}

function Invoke-SetupBuild([string[]]$Compose) {
    # the scheduler runs dbt for the dags, so its connection is the one that counts
    Write-Host 'checking the dbt connection'
    & docker @Compose exec -T airflow-scheduler dbt debug
    Assert-Ok 'dbt debug'

    # the setup selector (data_build_tool/selectors.yml): silver and gold are created empty, or keep what they hold
    # - its own target, setup-build, so it never writes airflow's manifest
    # - it builds what a load builds: never during a load
    # - single quotes leave the variables to bash, in the container
    Write-Host 'building the seeds, every model and elementary'
    & docker @Compose exec -T airflow-scheduler bash -c 'dbt build --selector setup --target-path $DBT_STATE_DIR/setup-build/target --log-path $DBT_STATE_DIR/setup-build/logs'
    Assert-Ok 'dbt build --selector setup'
}
