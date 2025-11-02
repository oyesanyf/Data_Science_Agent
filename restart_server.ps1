# Reliable Server Restart Script for Data Science Agent
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "RESTARTING DATA SCIENCE AGENT SERVER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Step 1: Kill all Python processes
Write-Host "`n[1/3] Stopping all Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Step 2: Verify port 8080 is free
Write-Host "[2/3] Checking port 8080..." -ForegroundColor Yellow
$port8080 = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if ($port8080) {
    Write-Host "   Port 8080 still in use by PID: $($port8080.OwningProcess)" -ForegroundColor Red
    Write-Host "   Force killing process..." -ForegroundColor Yellow
    Stop-Process -Id $port8080.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Verify port is free
$port8080 = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if ($port8080) {
    Write-Host "   [ERROR] Could not free port 8080" -ForegroundColor Red
    Write-Host "   Please close any browser tabs using http://localhost:8080" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "   [OK] Port 8080 is free" -ForegroundColor Green
}

# Step 3: Start server
Write-Host "[3/3] Starting server with new code (47 tools with __display__)..." -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

python start_server.py

