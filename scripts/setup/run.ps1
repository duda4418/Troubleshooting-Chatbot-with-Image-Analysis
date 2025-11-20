<#
scripts/setup/run.ps1
Docker Compose management script for the backend application.

Commands:
  run.ps1                 - Build images (using cache) and recreate containers
  run.ps1 -Rebuild        - Stop containers, remove volumes, rebuild images, start fresh
  run.ps1 -Start          - Recreate containers only (no build, use existing images)
  run.ps1 -Build          - Rebuild only the backend image and recreate backend container (for code changes)
  -NoCache                - Disable build cache (force rebuild from scratch)

Examples:
  .\run.ps1               # Quick restart with cached build
  .\run.ps1 -Rebuild      # Full clean rebuild (with cache)
  .\run.ps1 -Start        # Quick container restart (no build)
  .\run.ps1 -Build        # Rebuild backend only (with cache)
  .\run.ps1 -Rebuild -NoCache  # Full rebuild without cache (when dependencies change)
#>

Param(
    [switch]$Rebuild,
    [switch]$Start,
    [switch]$Build,
    [switch]$NoCache
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot

try {
    function Test-DockerRunning {
        Write-Host "Checking if Docker is running..." -ForegroundColor Blue
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            docker info > $null 2>&1
            return ($LASTEXITCODE -eq 0)
        } finally {
            $ErrorActionPreference = $oldPreference
        }
    }

    function Get-DockerComposeCommand {
        Write-Host "Detecting Docker Compose command..." -ForegroundColor Blue
        try {
            Write-Host "Trying 'docker compose version'..." -ForegroundColor Gray
            $null = docker compose version 2>$null
            Write-Host "Found 'docker compose' (v2)" -ForegroundColor Green
            return "docker compose"
        } catch {
            Write-Host "'docker compose' not found: $_" -ForegroundColor Yellow
            try {
                Write-Host "Trying 'docker-compose --version'..." -ForegroundColor Gray
                $null = docker-compose --version 2>$null
                Write-Host "Found 'docker-compose' (v1)" -ForegroundColor Green
                return "docker-compose"
            } catch {
                Write-Host "'docker-compose' not found: $_" -ForegroundColor Red
                return $null
            }
        }
    }

    if (-not (Test-DockerRunning)) {
        Write-Error "Docker daemon is not accessible. Please ensure Docker is running and the docker command is available, then try again."
        exit 1
    }

    $dockerComposeCmd = Get-DockerComposeCommand
    if (-not $dockerComposeCmd) {
        Write-Error "Docker Compose is not available. Please install Docker Compose or ensure it's included with your Docker setup."
        exit 1
    }

    Write-Host "Using Docker Compose command: $dockerComposeCmd" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Preparing Docker Compose actions..." -ForegroundColor Yellow

    $alembicPath = Join-Path (Join-Path "backend" "alembic") "versions"

    if ($Rebuild) {
        Write-Host "REBUILD requested: stopping and removing containers + volumes" -ForegroundColor Yellow
        Invoke-Expression "$dockerComposeCmd down -v --remove-orphans"

        Write-Host "Removing existing alembic versions..." -ForegroundColor Yellow
        if (Test-Path $alembicPath) {
            Remove-Item -Recurse -Force $alembicPath
            Write-Host "Alembic versions removed." -ForegroundColor Green
        } else {
            Write-Host "No alembic versions directory found." -ForegroundColor Gray
        }

        Write-Host "Building Docker images..." -ForegroundColor Yellow
        $buildCmd = "$dockerComposeCmd build"
        if ($NoCache) { $buildCmd += " --no-cache" }
        $buildCmd += " backend"
        Invoke-Expression $buildCmd
        if ($LASTEXITCODE -ne 0) { throw "docker compose build failed with exit code $LASTEXITCODE" }

        Write-Host "Starting containers..." -ForegroundColor Yellow
        Invoke-Expression "$dockerComposeCmd up -d"
        if ($LASTEXITCODE -ne 0) { throw "docker compose up failed with exit code $LASTEXITCODE" }

        Write-Host "Rebuild complete: images, containers and volumes recreated." -ForegroundColor Green
    } elseif ($Start) {
        Write-Host "START requested: recreating containers only (no build, no volume removal)" -ForegroundColor Yellow
        Invoke-Expression "$dockerComposeCmd up -d --force-recreate --remove-orphans"
        if ($LASTEXITCODE -ne 0) { throw "docker compose up failed with exit code $LASTEXITCODE" }
        Write-Host "Containers recreated." -ForegroundColor Green
    } elseif ($Build) {
        Write-Host "BUILD requested: rebuilding backend image and recreating backend container only" -ForegroundColor Yellow
        Invoke-Expression "$dockerComposeCmd stop backend"
        if ($LASTEXITCODE -ne 0) { throw "docker compose stop backend failed with exit code $LASTEXITCODE" }

        Write-Host "Building backend image..." -ForegroundColor Yellow
        $buildCmd = "$dockerComposeCmd build"
        if ($NoCache) { $buildCmd += " --no-cache" }
        $buildCmd += " backend"
        Invoke-Expression $buildCmd
        if ($LASTEXITCODE -ne 0) { throw "docker compose build backend failed with exit code $LASTEXITCODE" }

        Write-Host "Starting backend container..." -ForegroundColor Yellow
        Invoke-Expression "$dockerComposeCmd up -d backend"
        if ($LASTEXITCODE -ne 0) { throw "docker compose up backend failed with exit code $LASTEXITCODE" }

        Write-Host "Backend image rebuilt and container recreated." -ForegroundColor Green
    } else {
        Write-Host "Default action: rebuild images (using cache) and recreate containers" -ForegroundColor Yellow

        Write-Host "Building Docker images..." -ForegroundColor Yellow
        $buildCmd = "$dockerComposeCmd build"
        if ($NoCache) { $buildCmd += " --no-cache" }
        $buildCmd += " backend"
        Invoke-Expression $buildCmd
        if ($LASTEXITCODE -ne 0) { throw "docker compose build failed with exit code $LASTEXITCODE" }

        Write-Host "Starting containers (force recreate) ..." -ForegroundColor Yellow
        Invoke-Expression "$dockerComposeCmd up -d --force-recreate --remove-orphans"
        if ($LASTEXITCODE -ne 0) { throw "docker compose up failed with exit code $LASTEXITCODE" }

        Write-Host "Images built and containers recreated." -ForegroundColor Green
    }

    Write-Host ""; Write-Host "Your backend is running at: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API docs at: http://localhost:8000/docs" -ForegroundColor Cyan

} catch {
    Write-Host "Error during requested action: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}