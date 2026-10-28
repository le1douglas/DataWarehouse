# prod setup: builds the dbt and loader images of the git tag in RELEASE (docker/.env.prod), starts postgres and
# checks dbt's connection. the images are built from the tag's code: the repo is switched to the tag for the build
# and back to where it was after, even when the build fails.
# safe to run again: images of RELEASE that exist are not rebuilt, and up changes only what changed. loads nothing.
# needs the prod env files (01_setup_env.ps1), Docker Desktop running and no uncommitted changes. from the repo root:
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
    $missing = @('.env.prod', '.env.prod.loader', '.env.prod.transformer' | Where-Object { -not (Test-Path "docker\$_") })
    if ($missing.Count -gt 0) {
        throw "missing in docker\: $($missing -join ', '). run: powershell -ExecutionPolicy Bypass -File docker\01_setup_env.ps1"
    }

    if (-not (Test-Docker version --format '{{.Server.Version}}')) { throw 'docker does not answer: open Docker Desktop and wait until the engine runs' }

    $line = Select-String -Path docker\.env.prod -Pattern '^RELEASE=(.+)$' | Select-Object -First 1
    if (-not $line) { throw 'no RELEASE= line in docker\.env.prod' }
    $release = $line.Matches[0].Groups[1].Value.Trim()
    Write-Host "release $release"

    if ((Test-Docker image inspect "dbt:$release") -and (Test-Docker image inspect "loader:$release")) {
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
            & docker @prod build dbt loader
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

    Write-Host 'starting postgres'
    & docker @prod up -d
    Assert-Ok 'docker compose up'

    # over tcp: during the first start the init scripts run on a server that listens on the socket only, so a plain
    # pg_isready would answer before the DDL is done
    Write-Host 'waiting for postgres'
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-Docker @prod exec -T postgres pg_isready -h localhost -U postgres) { $ready = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw 'postgres is not ready after 2 minutes: see the logs of dw-prod-postgres-1 in Docker Desktop' }

    Write-Host 'checking the dbt connection'
    & docker @prod run --rm dbt debug
    Assert-Ok 'dbt debug'

    Write-Host "prod setup done, on $release"
}
finally {
    Pop-Location
}
