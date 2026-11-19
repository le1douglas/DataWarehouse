# prod setup: builds the images of the git tag in RELEASE (docker/.env.prod), starts the stack and builds every relation
# - the images are built from the tag's code: the repo is switched to it and back, even when the build fails
# - images of RELEASE that exist are not rebuilt
# - safe to run again, and needed again after a seed or a model changes. silver keeps what it holds
# - not during a load: up can recreate the scheduler and refreshes airflow's manifest, and the build touches silver
# - loads nothing: start a load dag in airflow (docs/INSTALLATION_GUIDE_DOCKER.md)
# needs the prod env file (01_setup_env.ps1), Docker Desktop running and no uncommitted changes. from the repo root:
#   powershell -ExecutionPolicy Bypass -File docker\03_setup_prod.ps1
$ErrorActionPreference = 'Stop'

. "$PSScriptRoot\setup_common.ps1"

$prod = @("compose", "-f", "docker/compose.yaml", "-f", "docker/compose.prod.yaml", "--env-file", "docker/.env.prod")

# the paths below are from the repo root
Push-Location (Resolve-Path "$PSScriptRoot\..")
try {
    Assert-Ready 'docker\.env.prod'

    $line = Select-String -Path docker\.env.prod -Pattern '^RELEASE=(.+)$' | Select-Object -First 1
    if (-not $line) { throw 'no RELEASE= line in docker\.env.prod' }
    $release = $line.Matches[0].Groups[1].Value.Trim()
    Write-Host "release $release"

    if ((Test-Docker image inspect "pipeline:$release") -and (Test-Docker image inspect "webapps:$release") -and (Test-Docker image inspect "datastreamer:$release")) {
        Write-Host "the images of $release exist, not rebuilt"
    }
    else {
        git rev-parse -q --verify "refs/tags/$release" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "no git tag ${release}: run git fetch --tags, or fix RELEASE in docker\.env.prod" }

        # the switch would carry uncommitted changes into the build, or refuse. ignored files, the env files, stay
        $changes = @(git status --porcelain --untracked-files=no)
        Assert-Ok 'git status'
        if ($changes.Count -gt 0) { throw 'uncommitted changes: commit or stash them first' }

        # where to come back to: the branch, or the commit when HEAD is already detached
        $origin = git symbolic-ref --short -q HEAD
        if (-not $origin) { $origin = git rev-parse HEAD }

        Write-Host "switching to $release to build its images"
        git switch --detach $release
        Assert-Ok "git switch to $release"
        try {
            # the airflow services share one image, built through airflow-init
            & docker @prod build airflow-init webapps datastreamer
            Assert-Ok 'the build'
        }
        finally {
            Write-Host "switching back to $origin"
            # a branch is switched to by name, a commit with --detach
            git show-ref -q --verify "refs/heads/$origin"
            if ($LASTEXITCODE -eq 0) { git switch $origin } else { git switch --detach $origin }
            Assert-Ok "git switch back to $origin"
        }
    }

    Start-Warehouse $prod

    Invoke-SetupBuild $prod

    Write-Host "prod setup done, on $release"
}
finally {
    Pop-Location
}
