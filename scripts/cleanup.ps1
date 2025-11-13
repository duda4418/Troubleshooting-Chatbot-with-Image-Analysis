<#
scripts/cleanup.ps1
Clean up Docker resources for this project.

Usage:
  ./cleanup.ps1                 # containers only (keep images & volumes)
  ./cleanup.ps1 -f              # containers + images (keep volumes)
  ./cleanup.ps1 -Force          # same as -f
  ./cleanup.ps1 -Nuke           # containers + images + volumes

Notes:
- Works with both "docker compose" (v2) and "docker-compose" (v1).
- Uses --remove-orphans so stray compose containers are also cleaned.
#>

param(
    [Alias('f')]
    [switch]$Force,
    [switch]$Nuke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-DockerRunning {
    Write-Host "Checking if Docker is running..." -ForegroundColor Blue
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        docker info > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Docker is running." -ForegroundColor Green
            return $true
        } else {
            Write-Host "Docker info failed with exit code $LASTEXITCODE" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "Error checking Docker: $_" -ForegroundColor Red
        return $false
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

function Get-DockerComposeCommand {
    Write-Host "Detecting Docker Compose command..." -ForegroundColor Blue
    try {
        $null = docker compose version 2>$null
        Write-Host "Found 'docker compose' (v2)" -ForegroundColor Green
        return "docker compose"
    } catch {
        try {
            $null = docker-compose --version 2>$null
            Write-Host "Found 'docker-compose' (v1)" -ForegroundColor Green
            return "docker-compose"
        } catch {
            Write-Host "No Docker Compose command found." -ForegroundColor Red
            return $null
        }
    }
}

if (-not (Test-DockerRunning)) {
    Write-Error "Docker daemon is not accessible. Start Docker Desktop/Rancher Desktop and ensure 'docker' is in PATH."
    exit 1
}

$dockerComposeCmd = Get-DockerComposeCommand
if (-not $dockerComposeCmd) {
    Write-Error "Docker Compose is not available. Please install it or ensure it's included with your Docker setup."
    exit 1
}

Write-Host "Using Docker Compose command: $dockerComposeCmd" -ForegroundColor Blue
Write-Host ""

# If both switches are provided, prioritize -Nuke
if ($Nuke) {
    Write-Host "NUKE MODE: removing containers + images + volumes..." -ForegroundColor Red
    try {
        # Project-scoped nuke: remove containers, images, and volumes defined by compose
        Invoke-Expression "$dockerComposeCmd down -v --rmi all --remove-orphans"
        Write-Host "Done. Containers, images, and volumes removed for this project." -ForegroundColor Green
    } catch {
        Write-Host "Nuke failed: $_" -ForegroundColor Red
        exit 1
    }
    exit 0
}

if ($Force) {
    Write-Host "FORCE MODE: removing containers + images (keeping volumes)..." -ForegroundColor Yellow
    try {
        Invoke-Expression "$dockerComposeCmd down --rmi all --remove-orphans"
        Write-Host "Done. Containers and images removed (volumes preserved)." -ForegroundColor Green
    } catch {
        Write-Host "Force cleanup failed: $_" -ForegroundColor Red
        exit 1
    }
    exit 0
}

# Default: containers only
Write-Host "Default cleanup: removing containers (keeping images & volumes)..." -ForegroundColor Yellow
try {
    Invoke-Expression "$dockerComposeCmd down --remove-orphans"
    Write-Host "Done. Containers removed; images and volumes preserved." -ForegroundColor Green
} catch {
    Write-Host "Cleanup failed: $_" -ForegroundColor Red
    exit 1
}
