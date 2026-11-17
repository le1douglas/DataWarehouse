# dev setup: builds the pipeline, webapps and dev images, starts postgres, creates the airflow database when it is missing,
# starts airflow and the web apps (airflow-init installs the dbt packages and refreshes airflow's manifest), installs
# the meltano plugins, checks dbt's connection and builds everything no load builds (the dbt selector setup,
# DataWarehouseDbt/selectors.yml). the steps both setups share are in setup_common.ps1.
# safe to run again: up and build change only what changed, the airflow database is created only once, dbt deps and
# meltano install reinstall the same versions, airflow's manifest is refreshed, and the setup build rebuilds the seeds,
# the ref_ models and the dims over them: run it again after one of them changes. not while a load runs: up refreshes
# airflow's manifest, and can recreate the scheduler.
# loads nothing: a load dag, in the airflow ui (see docs/INSTALLATION_GUIDE_DOCKER.md)
# needs the env file (01_setup_env.ps1) and Docker Desktop running. from the repo root:
#   powershell -ExecutionPolicy Bypass -File docker\02_setup_dev.ps1
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\setup_common.ps1"

$dev = @("compose", "-f", "docker/compose.yaml", "-f", "docker/compose.dev.yaml")

# the paths below are from the repo root (the compose files and env files are in docker/)
Push-Location (Resolve-Path "$PSScriptRoot\..")
try {
    Assert-Ready 'docker\.env'

    # before up, so up starts the services on the new images, not on the ones of the last build. the airflow services
    # share one image: building airflow-init builds it for all of them
    Write-Host 'building the pipeline, webapps and dev images'
    & docker @dev --profile dev build airflow-init webapps dev
    Assert-Ok 'the build'

    Start-Warehouse $dev

    # dev keeps its own meltano plugins in the meltano-plugins volume (docker/compose.dev.yaml): the repo mount hides the
    # ones installed in the image
    Write-Host 'installing the meltano plugins'
    & docker @dev exec -T airflow-scheduler meltano install
    Assert-Ok 'meltano install'

    Invoke-SetupBuild $dev

    Write-Host 'dev setup done. next: a load dag, in the airflow ui (see docs/INSTALLATION_GUIDE_DOCKER.md)'
}
finally {
    Pop-Location
}
