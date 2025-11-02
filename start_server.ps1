# Data Science Agent Startup Script
# This script starts the agent with web interface enabled and auto-installs all 77 tools
#
# Note: This script uses 'uv sync' to handle dependency installation.
# The main.py auto_install_dependencies() function verifies packages are installed.
#
# IMPORTANT: Some packages have different pip names vs import names:
#   - pip: imbalanced-learn     → import: imblearn
#   - pip: sentence-transformers → import: sentence_transformers
#   - pip: alibi-detect         → import: alibi_detect
#   - pip: faiss-cpu/faiss-gpu  → import: faiss
#   - pip: python-dotenv        → import: dotenv
#   - pip: scikit-learn         → import: sklearn
#
# CRITICAL VERSION CONSTRAINTS:
#   - numpy MUST be <2.0 (opencv-python requires numpy 1.x)
#   - opencv-python >=4.8.0 required by AutoGluon multimodal
#   - If you get "RuntimeError: empty_like method already has a different docstring"
#     → Run: fix_numpy_opencv.bat to fix numpy version

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host "Starting Data Science Agent with Web Interface" -ForegroundColor Green

# Suppress pkg_resources warnings from AutoGluon in all subprocesses
$env:PYTHONWARNINGS = "ignore::UserWarning:pkg_resources,ignore::DeprecationWarning:pkg_resources"
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host ""

# Clear Python bytecode cache to prevent stale imports
Write-Host "Clearing Python bytecode cache..." -ForegroundColor Yellow
$pycacheDirs = Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory -Force -ErrorAction SilentlyContinue
if ($pycacheDirs) {
    $pycacheDirs | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Cache cleared (prevents stale imports)" -ForegroundColor Green
} else {
    Write-Host "[OK] Cache already clean" -ForegroundColor Green
}
Write-Host ""

# Kill any existing process on port 8080
Write-Host "Checking for existing server on port 8080..." -ForegroundColor Yellow
$existingProcess = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($existingProcess) {
    Write-Host "Found existing process (PID: $existingProcess). Stopping it..." -ForegroundColor Yellow
    Stop-Process -Id $existingProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "[OK] Existing server stopped" -ForegroundColor Green
    Write-Host ""
}

# Enable web interface
$env:SERVE_WEB_INTERFACE = "true"
$env:SKIP_DEPENDENCY_CHECK = "true"

# Ensure we're using uv environment and install all dependencies
Write-Host "Syncing dependencies with uv (includes 77 ML tools)..." -ForegroundColor Yellow
$syncResult = uv sync 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Failed to sync dependencies with uv" -ForegroundColor Red
    Write-Host "Make sure 'uv' is installed: https://docs.astral.sh/uv/" -ForegroundColor Yellow
    Write-Host $syncResult
    Write-Host ""
    Write-Host "To install uv, run: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"" -ForegroundColor Cyan
    exit 1
}

Write-Host "[OK] All dependencies synced successfully!" -ForegroundColor Green
Write-Host "     150+ tools ready: AutoML, Sklearn, Fairness, Drift, Causal, HPO, and more" -ForegroundColor Cyan
Write-Host "     All tools now use ADK-safe wrappers for optimal performance!" -ForegroundColor Green
Write-Host "     " -NoNewline
Write-Host "✅ Streaming tools ENABLED" -ForegroundColor Green -NoNewline
Write-Host " for real-time progress updates!" -ForegroundColor Cyan
Write-Host ""

# Start the server using uv
Write-Host "Starting server on http://localhost:8080" -ForegroundColor Cyan
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host ""

uv run python main.py

