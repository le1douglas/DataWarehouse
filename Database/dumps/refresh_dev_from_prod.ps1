# dev refresh: dev's database becomes a copy of prod's. a convenience for development, not a backup of prod.
#   1. writes a prod dump (pg_dump -Fc) into this folder, named with the local time: DataWarehouse_prod_<time>.dump
#   2. drops dev's database, disconnecting everyone on it (Excel, VS Code SQL tabs), and recreates it from the dump
# both stacks must be up. from the repo root:
#   powershell -ExecutionPolicy Bypass -File Database\dumps\refresh_dev_from_prod.ps1
# or, to restore a dump that is already here, without writing a new one:
#   powershell -ExecutionPolicy Bypass -File Database\dumps\refresh_dev_from_prod.ps1 -DumpFile DataWarehouse_prod_<time>.dump
# the dumps (*.dump) are ignored by git. prod mounts this folder at /dumps read-write, dev read only

param(
    # the file name of an existing dump in this folder. empty: write a new one from prod first
    [string]$DumpFile = ""
)

# windows powershell 5.1 does not stop on a failed native command, so every docker call is checked with Assert-Ok
function Assert-Ok([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit code $LASTEXITCODE). dev was left as it is, unless the step was the restore" }
}

$database = "DataWarehouse"
$prod = @("compose", "-f", "docker/compose.yaml", "-f", "docker/compose.prod.yaml", "--env-file", "docker/.env.prod")
$dev = @("compose", "-f", "docker/compose.yaml", "-f", "docker/compose.dev.yaml")

# the paths below are from the repo root (the compose files and env files are in docker/)
Push-Location (Resolve-Path "$PSScriptRoot\..\..")
try {
    if ($DumpFile -eq "") {
        # the time comes from windows: the postgres container's clock is in UTC
        $DumpFile = "DataWarehouse_prod_$(Get-Date -Format yyyy-MM-dd_HHmmss).dump"
        Write-Host "writing the prod dump $DumpFile"
        & docker @prod exec -T postgres pg_dump -U postgres -d $database -Fc -f "/dumps/$DumpFile"
        Assert-Ok "the prod dump"
    }
    elseif (-not (Test-Path "Database\dumps\$DumpFile")) {
        throw "no dump Database\dumps\$DumpFile"
    }

    # WITH (FORCE) disconnects every session on dev's database in the same statement as the drop, so none can come
    # back in between. through stdin: psql -c from powershell loses the double quotes around "DataWarehouse"
    Write-Host "dropping dev's database $database, disconnecting everyone on it"
    "DROP DATABASE IF EXISTS `"$database`" WITH (FORCE);" | & docker @dev exec -T postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1 -q
    Assert-Ok "the drop of dev's database"

    # --create recreates the database from the dump, connected to the maintenance database postgres meanwhile
    Write-Host "restoring $DumpFile into dev"
    & docker @dev exec -T postgres pg_restore -U postgres -d postgres --create --exit-on-error "/dumps/$DumpFile"
    Assert-Ok "the restore into dev (dev's database may be missing or incomplete: run the script again)"

    Write-Host "rows in dev's dw_bronze.brnz_journal_entries:"
    "SELECT count(*) FROM dw_bronze.brnz_journal_entries;" | & docker @dev exec -T postgres psql -U postgres -d $database -tA
    Assert-Ok "the check of dev"
    Write-Host "dev refresh done. dev now holds prod's data as of $DumpFile"
}
finally {
    Pop-Location
}
