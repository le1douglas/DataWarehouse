# dev setup: builds the images, starts the stack, installs the meltano plugins and builds every relation
# - safe to run again, and needed again after a seed or a model changes. silver keeps what it holds
# - not during a load: up can recreate the scheduler and refreshes airflow's manifest, and the build touches silver
# - loads nothing: start a load dag in airflow (docs/INSTALLATION_GUIDE_DOCKER.md)
# needs the env file (01_setup_env.ps1) and Docker Desktop running. from the repo root:
#   powershell -ExecutionPolicy Bypass -File docker\02_setup_dev.ps1
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\setup_common.ps1"

$dev = @("compose", "-f", "docker/compose.yaml", "-f", "docker/compose.dev.yaml")

# the paths below are from the repo root
Push-Location (Resolve-Path "$PSScriptRoot\..")
try {
    Assert-Ready 'docker\.env'

    # before up, so up starts the new images. the airflow services share one image, built through airflow-init
    Write-Host 'building the pipeline, webapps and dev images'
    & docker @dev --profile dev build airflow-init webapps dev
    Assert-Ok 'the build'

    Start-Warehouse $dev

    # dev's plugins are in a volume (docker/compose.dev.yaml): the repo mount hides the image's
    Write-Host 'installing the meltano plugins'
    & docker @dev exec -T airflow-scheduler meltano install
    Assert-Ok 'meltano install'

    Invoke-SetupBuild $dev

    Write-Host 'dev setup done. next: a load dag, in the airflow ui (see docs/INSTALLATION_GUIDE_DOCKER.md)'
}
finally {
    Pop-Location
}
