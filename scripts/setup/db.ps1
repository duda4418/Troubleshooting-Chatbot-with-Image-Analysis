<#
scripts/db.ps1
Database lifecycle driver for Postgres (SQLModel + Alembic) inside Compose.

Usage:
  ./scripts/db.ps1 -Init
  ./scripts/db.ps1 -Revision -Message "add groups"
  ./scripts/db.ps1 -Upgrade            # to 'head'
  ./scripts/db.ps1 -Downgrade -Rev -1  # one step back
  ./scripts/db.ps1 -Backup             # to ./backups/backup-<db>-<ts>.sql
  ./scripts/db.ps1 -Restore -File .\backups\backup-appdb-2025....sql
  ./scripts/db.ps1 -Rebuild            # drop volumes, recreate schema, upgrade head

Options:
  -Project <name>   Compose project (default: folder name)
  -Rev <revision>   Alembic target (default: head)
#>

param(
  [switch]$Init,
  [switch]$Revision,
  [string]$Message = "",
  [switch]$Upgrade,
  [switch]$Downgrade,
  [string]$Rev = "head",
  [switch]$Backup,
  [switch]$Restore,
  [string]$File,
  [switch]$Rebuild,
  [string]$Project,
  [Alias('f')][switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
$backendRoot = Resolve-Path (Join-Path $repoRoot "backend")
$backendVolumeSpec = (($backendRoot.Path -replace "\\", "/").TrimEnd("/")) + ":/app"

try {

function Normalize-ProjectName {
  param([string]$Name)

  if (-not $Name) { return "app" }

  $lower = $Name.ToLowerInvariant()
  $normalized = ($lower -replace "[^a-z0-9_-]", "-")
  $normalized = $normalized.Trim("-")

  if (-not $normalized) {
    $normalized = "app"
  }

  if ($normalized[0] -notmatch "[a-z0-9]") {
    $normalized = "proj-$normalized"
  }

  return $normalized
}

function Get-ProjectName {
  $raw = if ($Project) { $Project } else { Split-Path -Leaf (Get-Location) }
  return Normalize-ProjectName $raw
}

function Test-DockerRunning {
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try { docker info > $null 2>&1; return ($LASTEXITCODE -eq 0) } finally { $ErrorActionPreference = $old }
}

# Return parts so we can invoke: & $Exe @Sub @Args
function Get-ComposeParts {
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try {
    docker compose version > $null 2>&1
    $ErrorActionPreference = $old
    return @{ Exe = "docker"; Sub = @("compose") }  # v2
  } catch {
    try {
      docker-compose --version > $null 2>&1
      $ErrorActionPreference = $old
      return @{ Exe = "docker-compose"; Sub = @() } # v1
    } catch {
      $ErrorActionPreference = $old
      throw "Neither 'docker compose' nor 'docker-compose' is available."
    }
  }
}

# Compose runner
function Compose-Run {
  param([Parameter(ValueFromRemainingArguments=$true)] [string[]]$Args)
  & $script:ComposeExe @script:ComposeSub @Args
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed ($LASTEXITCODE): $($script:ComposeExe) $($script:ComposeSub -join ' ') $($Args -join ' ')"
  }
}

function Compose-RunBackend {
  param(
    [Parameter(ValueFromRemainingArguments=$true)] [string[]]$Args,
    [switch]$MountBackend
  )

  $prefix = @("-p",$script:ProjectName,"run","--rm")
  if ($MountBackend) {
    $prefix += @("-v",$script:BackendVolumeSpec)
  }
  $fullArgs = $prefix + @("backend") + $Args
  Compose-Run -Args $fullArgs
}

function Get-DbContainerId {
  $id = Compose-Run -Args @("-p",$script:ProjectName,"ps","-q","db")
  if (-not $id) { throw "DB container not found for project '$($script:ProjectName)'. Start stack first (run.ps1) or 'docker compose up -d db'." }
  return $id.Trim()
}

function Wait-DbHealthy {
  Write-Host "Waiting for db health..." -ForegroundColor Cyan
  $dbUser = $env:POSTGRES_USER; if (-not $dbUser) { $dbUser = "postgres" }
  $dbName = $env:POSTGRES_DB;   if (-not $dbName) { $dbName = "appdb" }

  # Get the actual container ID from compose
  $dbId = Get-DbContainerId

  for ($i=0; $i -lt 60; $i++) {
    # 1) Preferred: read container health status
    $status = (docker inspect $dbId --format '{{.State.Health.Status}}' 2>$null).Trim()
    if ($status -eq 'healthy') {
      Write-Host "DB is healthy." -ForegroundColor Green
      return
    }

    # 2) Fallback: use pg_isready (in case healthcheck isn't available yet)
    docker exec $dbId pg_isready -U $dbUser -d $dbName *>$null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "DB is accepting connections (pg_isready)." -ForegroundColor Green
      return
    }

    Start-Sleep -Seconds 1
  }

  Write-Warning "DB did not report healthy within the timeout; continuing anyway."
}

if (-not (Test-DockerRunning)) { Write-Error "Docker daemon not accessible."; exit 1 }

$parts = Get-ComposeParts
$script:ComposeExe = $parts.Exe
$script:ComposeSub = $parts.Sub
$script:ProjectName = Get-ProjectName
$script:BackendVolumeSpec = $backendVolumeSpec

$composePretty = "$ComposeExe" + ($(if ($ComposeSub.Count) { " " + ($ComposeSub -join ' ') } else { "" }))
Write-Host "Using: $composePretty  (project=$ProjectName)" -ForegroundColor Blue

# -------- INIT --------
if ($Init) {
  Write-Host "Generating initial migration from models and upgrading to head..." -ForegroundColor Yellow
  # Ensure db is up for autogenerate
  # If there are leftover migration files, offer to remove them to avoid autogenerate conflicts
  $versionsDir = Join-Path (Join-Path "backend" "alembic") "versions"
  if (Test-Path $versionsDir) {
  $existing = @(Get-ChildItem -Path $versionsDir -File -ErrorAction SilentlyContinue)
    if ($existing -and $existing.Count -gt 0) {
  Write-Host "Detected existing files in ${versionsDir}:" -ForegroundColor Yellow
      $existing | ForEach-Object { Write-Host " - $($_.Name)" }
      if ($Force) {
        Write-Host "-Force supplied: removing existing migration files..." -ForegroundColor Yellow
        $remove = $true
      } else {
        $answer = Read-Host "Remove these files before init? (y/N)"
        $remove = ($answer -and $answer.ToLower().StartsWith('y'))
      }
      if ($remove) {
        Write-Host "Removing existing migration files..." -ForegroundColor Yellow
        Get-ChildItem -Path $versionsDir -File | Remove-Item -Force
        Write-Host "Removed files in $versionsDir" -ForegroundColor Green
      } else {
        Write-Host "Keeping existing migration files. Be aware autogenerate may produce conflicts." -ForegroundColor Cyan
      }
    }
  }

  Compose-Run -Args @("-p",$ProjectName,"up","-d","db","--remove-orphans") | Out-Null
  Wait-DbHealthy
  if (!(Test-Path $versionsDir)) { New-Item -ItemType Directory $versionsDir | Out-Null }
  Compose-RunBackend -MountBackend -Args @("alembic","revision","--autogenerate","-m","initial schema")
  Compose-RunBackend -MountBackend -Args @("alembic","upgrade","head")
  Write-Host "Init complete." -ForegroundColor Green
  exit 0
}

# -------- REVISION --------
if ($Revision) {
  if (-not $Message) { throw "Use -Message 'description' for the revision message." }
  Compose-Run -Args @("-p",$ProjectName,"up","-d","db","--remove-orphans") | Out-Null
  Wait-DbHealthy
  Compose-RunBackend -MountBackend -Args @("alembic","revision","--autogenerate","-m",$Message)
  Write-Host "Revision created." -ForegroundColor Green
  exit 0
}

# -------- UPGRADE / DOWNGRADE --------
if ($Upgrade) {
  Compose-Run -Args @("-p",$ProjectName,"up","-d","db","--remove-orphans") | Out-Null
  Wait-DbHealthy
  Compose-RunBackend -MountBackend -Args @("alembic","upgrade",$Rev)
  Write-Host "Upgrade complete." -ForegroundColor Green
  exit 0
}
if ($Downgrade) {
  Compose-RunBackend -MountBackend -Args @("alembic","downgrade",$Rev)
  Write-Host "Downgrade complete." -ForegroundColor Green
  exit 0
}

# -------- BACKUP --------
if ($Backup) {
  $DbName = $env:POSTGRES_DB; if (-not $DbName) { $DbName = "appdb" }
  $User = $env:POSTGRES_USER; if (-not $User) { $User = "postgres" }
  $outDir = "backups"; if (!(Test-Path $outDir)) { New-Item -ItemType Directory $outDir | Out-Null }
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $file = Join-Path $outDir "backup-$DbName-$stamp.sql"

  $dbC = Get-DbContainerId
  Write-Host "Creating backup: $file" -ForegroundColor Yellow
  docker exec $dbC pg_dump -U $User -d $DbName > $file
  Write-Host "Backup done." -ForegroundColor Green
  exit 0
}

# -------- RESTORE --------
if ($Restore) {
  if (-not $File) { throw "Provide -File <path_to_sql_dump>" }
  if (!(Test-Path $File)) { throw "File not found: $File" }
  $DbName = $env:POSTGRES_DB; if (-not $DbName) { $DbName = "appdb" }
  $User = $env:POSTGRES_USER; if (-not $User) { $User = "postgres" }

  $dbC = Get-DbContainerId
  Write-Host "Restoring $File ..." -ForegroundColor Yellow
  Get-Content -Raw $File | docker exec -i $dbC psql -U $User -d $DbName
  Write-Host "Restore done." -ForegroundColor Green
  exit 0
}

# -------- REBUILD (recreate db + redis only) --------
if ($Rebuild) {
  Write-Host "Rebuild: recreating 'db' and 'redis' services (containers + service volumes) only..." -ForegroundColor Red

  # Remove the db and redis containers (and anonymous volumes attached to them) only.
  # This avoids bringing down the entire compose project and preserves other services.
  Write-Host "Removing existing 'db' and 'redis' containers (if present)..." -ForegroundColor Yellow
  Compose-Run -Args @("-p",$ProjectName,"rm","-s","-f","-v","db","redis") | Out-Null

  # Recreate db and redis without affecting other services (--no-deps + --force-recreate)
  Write-Host "Recreating 'db' and 'redis'..." -ForegroundColor Yellow
  Compose-Run -Args @("-p",$ProjectName,"up","-d","--no-deps","--force-recreate","db","redis") | Out-Null

  Wait-DbHealthy
  # Run migrations after db is healthy using the live backend sources
  Compose-RunBackend -MountBackend -Args @("alembic","upgrade","head")
  Write-Host "Rebuild complete (db + redis)." -ForegroundColor Green
  exit 0
}

Write-Host "Nothing to do. Use one of: -Init | -Revision -Message '...' | -Upgrade | -Downgrade -Rev X | -Backup | -Restore -File file.sql | -Rebuild" -ForegroundColor Yellow

} finally {
  Pop-Location
}
