# prod setup: builds the pipeline, webapps and datastreamer images of the git tag in RELEASE (docker/.env.prod), starts
# postgres, creates the airflow database when it is missing, starts the rest and checks dbt's connection. the images are
# built from the tag's code: the repo is switched to the tag for the build and back to where it was after, even when the
# build fails.
# safe to run again: images of RELEASE that exist are not rebuilt, the airflow database is created only once, and up
# changes only what changed. loads nothing.
# needs the prod env file (01_setup_env.ps1), Docker Desktop running and no uncommitted changes. from the repo root:
#   powershell -ExecutionPolicy Bypass -File docker\03_setup_prod.ps1
$ErrorActionPreference = 'Stop'

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

$prod = @("compose", "-f", "docker/compose.yaml", "-f", "docker/compose.prod.yaml", "--env-file", "docker/.env.prod")

# the paths below are from the repo root (the compose files and env files are in docker/)
Push-Location (Resolve-Path "$PSScriptRoot\..")
try {
    if (-not (Test-Path 'docker\.env.prod')) {
        throw 'missing: docker\.env.prod. run: powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1'
    }

    if (-not (Test-Docker version --format '{{.Server.Version}}')) { throw 'docker does not answer: open Docker Desktop and wait until the engine runs' }

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

        # the switch would carry uncommitted changes into the build, or refuse. ignored files (the env files) stay
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
            # the airflow services share one image: building airflow-init builds it for all of them
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

    # postgres alone first: airflow-init needs the airflow database, which the init scripts make only on an empty volume.
    # --wait returns once the healthcheck of docker/compose.yaml passes, which is checked over tcp, so after the init scripts
    Write-Host 'starting postgres'
    & docker @prod up -d --wait postgres
    Assert-Ok 'starting postgres'

    # a volume from before airflow has no airflow database: made with the same script the init folder runs
    $exists = & docker @prod exec -T postgres psql -U postgres -d postgres -Atc "select 1 from pg_database where datname = 'airflow'"
    Assert-Ok 'looking for the airflow database'
    if ($exists -ne '1') {
        Write-Host 'creating the airflow database'
        & docker @prod exec -T postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/00_create_airflow_database.sql
        Assert-Ok 'creating the airflow database'
    }

    # airflow-init migrates the airflow database first, then the other airflow services start
    Write-Host 'starting airflow and the web apps'
    & docker @prod up -d
    Assert-Ok 'docker compose up'

    # the scheduler runs dbt, so its connection is the one that counts
    Write-Host 'checking the dbt connection'
    & docker @prod exec -T airflow-scheduler dbt debug
    Assert-Ok 'dbt debug'

    Write-Host "prod setup done, on $release"
}
finally {
    Pop-Location
}
