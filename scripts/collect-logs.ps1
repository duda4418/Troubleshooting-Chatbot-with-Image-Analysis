Param(
    [switch]$Reproduce,
    [switch]$Follow
)

# Collect compose status and container logs for api/db/redis into ./logs/<timestamp>
$PROJECT = Split-Path -Leaf (Get-Location)
$DC = "docker"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logdir = Join-Path -Path (Get-Location) -ChildPath "logs\$timestamp"
New-Item -ItemType Directory -Path $logdir -Force | Out-Null

Write-Output "Collecting Docker Compose status and logs into: $logdir"

try {
    Write-Output "-- docker compose ps --"
    & $DC 'compose' -p $PROJECT ps | Tee-Object -FilePath (Join-Path $logdir "compose_ps.txt")
} catch {
    Write-Error "Failed to run 'docker compose ps'. Is Docker installed and running? $_"
    exit 1
}

# Get container ids
$API_ID  = ((& $DC 'compose' -p $PROJECT ps -q api) -join "").Trim()
$DB_ID   = ((& $DC 'compose' -p $PROJECT ps -q db) -join "").Trim()
$REDIS_ID= ((& $DC 'compose' -p $PROJECT ps -q redis) -join "").Trim()

Set-Content -Path (Join-Path $logdir "container_ids.txt") -Value @("api=$API_ID","db=$DB_ID","redis=$REDIS_ID") -Force

Write-Output "Container ids saved to container_ids.txt"

# Capture recent logs for each service
$services = @('api','db','redis')
foreach ($svc in $services) {
    $outFile = Join-Path $logdir "$svc.log"
    Write-Output "Saving last 500 lines of logs for service: $svc -> $outFile"
    & $DC 'compose' -p $PROJECT logs --no-color $svc --tail 500 | Tee-Object -FilePath $outFile | Out-Null
}

# Search api logs for tracebacks/errors
$errFile = Join-Path $logdir "api_errors.log"
& $DC 'compose' -p $PROJECT logs --no-color api --tail 2000 | Select-String -Pattern 'Traceback|ERROR|Exception' | Tee-Object -FilePath $errFile | Out-Null

Write-Output "Saved api_errors.log (matches for Traceback/ERROR/Exception)."

if ($Reproduce) {
    Write-Output "Reproducing the failing request to http://127.0.0.1:8000/test/roles"
    try {
        curl.exe -s -v http://127.0.0.1:8000/test/roles > (Join-Path $logdir "last_response.txt") 2>&1
        Write-Output "Saved HTTP response to last_response.txt"
    } catch {
        Write-Error "curl.exe failed: $_"
    }

    # capture logs after request
    & $DC 'compose' -p $PROJECT logs --no-color api --tail 500 | Tee-Object -FilePath (Join-Path $logdir "api_after_request.log") | Out-Null
    Write-Output "Saved api_after_request.log"
}

Write-Output "Logs collected. Files in: $logdir"
Get-ChildItem -Path $logdir | ForEach-Object { Write-Output $_.FullName }

if ($Follow) {
    Write-Output "Streaming api logs (Ctrl+C to stop). Output will also be appended to $logdir\api_stream.log"
    & $DC 'compose' -p $PROJECT logs --no-color -f api | Tee-Object -FilePath (Join-Path $logdir "api_stream.log")
}

Write-Output "Finished. Paste the contents of the important files (api_errors.log, api_after_request.log, api.log, db.log) here for debugging."
