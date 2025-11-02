# FORCE RESTART - Aggressive cache clearing + fresh start
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "FORCE RESTART - CLEARING ALL CACHES" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill all Python
Write-Host "[1/5] Killing all Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Write-Host "   ✓ Done" -ForegroundColor Green
Write-Host ""

# Step 2: Clear ALL bytecode caches
Write-Host "[2/5] Clearing bytecode caches..." -ForegroundColor Yellow
Remove-Item -Recurse -Force data_science\__pycache__ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force data_science\**\__pycache__ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .venv\Lib\site-packages\data_science\__pycache__ -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Recurse -Filter "*.pyc" -File | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "   ✓ All bytecode cleared" -ForegroundColor Green
Write-Host ""

# Step 3: Check critical fix
Write-Host "[3/5] Verifying RULE #1 in code..." -ForegroundColor Yellow
$ruleCheck = Select-String -Path "data_science\agent.py" -Pattern "RULE #1 \(MOST IMPORTANT" -Quiet
if ($ruleCheck) {
    Write-Host "   ✓ RULE #1 found at top of instructions" -ForegroundColor Green
    Write-Host "   → 'FORBIDDEN: didn''t render, no data'" -ForegroundColor Green
} else {
    Write-Host "   ✗ RULE #1 NOT FOUND - FIX MAY NOT BE APPLIED!" -ForegroundColor Red
}
Write-Host ""

# Step 4: Show what fix does
Write-Host "[4/5] What RULE #1 Does:" -ForegroundColor Yellow
Write-Host "   Before: 'preview didn''t render in output stream'" -ForegroundColor Red
Write-Host "   After:  Shows actual data table from __display__" -ForegroundColor Green
Write-Host ""
Write-Host "   Before: 'no specific details were provided'" -ForegroundColor Red
Write-Host "   After:  Shows actual statistics/numbers" -ForegroundColor Green
Write-Host ""

# Step 5: Start server
Write-Host "[5/5] Starting server..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

python start_server.py

