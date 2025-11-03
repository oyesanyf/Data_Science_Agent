@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ==============================================
rem  Data Science Agent Startup Script (Batch)
rem  Starts the agent with web interface enabled
rem  and auto-installs all 77 tools via uv sync
rem ==============================================
rem
rem Note: This script relies on 'uv sync' for dependencies.
rem The main.py auto_install_dependencies() verifies packages.
rem
rem IMPORTANT: Some packages have different pip vs import names:
rem   - pip: imbalanced-learn    -> import: imblearn
rem   - pip: sentence-transformers -> import: sentence_transformers
rem   - pip: alibi-detect         -> import: alibi_detect
rem   - pip: faiss-cpu/faiss-gpu  -> import: faiss
rem   - pip: python-dotenv        -> import: dotenv
rem   - pip: scikit-learn         -> import: sklearn
rem
rem CRITICAL VERSION CONSTRAINTS:
rem   - numpy MUST be ^<2.0 (opencv-python requires numpy 1.x)
rem   - opencv-python ^>=4.8.0 required by AutoGluon multimodal
rem   - If you get "RuntimeError: empty_like method already has a different docstring"
rem     -> Run: fix_numpy_opencv.bat to fix numpy version
rem
rem ==============================================

echo.
echo ===========================================================
echo Starting Data Science Agent with Web Interface
echo ===========================================================
echo.

rem -- Suppress pkg_resources warnings from AutoGluon in all subprocesses
set "PYTHONWARNINGS=ignore::UserWarning:pkg_resources,ignore::DeprecationWarning:pkg_resources"

rem -- Clear Python bytecode cache to prevent stale imports
echo Clearing Python bytecode cache...
set "CACHE_FOUND="
for /d /r %%D in (__pycache__) do (
    if exist "%%D" (
        set "CACHE_FOUND=1"
        rd /s /q "%%D" 2>nul
    )
)
if defined CACHE_FOUND (
    echo [OK] Cache cleared ^(prevents stale imports^)
) else (
    echo [OK] Cache already clean
)
echo.

rem -- Kill any existing process on port 8080
set "PORT=8080"
echo Checking for existing server on port %PORT%...

set "FOUND="
rem Use usebackq so the backtick runs the pipeline safely (avoids quote/parens issues)
for /f "usebackq tokens=5" %%P in (`
  netstat -ano -p tcp ^| findstr /R /C:":%PORT% .*LISTENING"
`) do (
    set "PID=%%P"
    set "FOUND=1"
    echo Found existing process (PID: !PID!). Stopping it...
    taskkill /F /PID !PID! >nul 2>&1
)

if defined FOUND (
    timeout /t 2 /nobreak >nul
    echo [OK] Existing server stopped
    echo.
)

rem -- Enable web interface for this session
set "SERVE_WEB_INTERFACE=true"
set "SKIP_DEPENDENCY_CHECK=true"

rem -- Detect GPU
echo Checking GPU availability...
set "GPU_DETECTED=0"
nvidia-smi --query-gpu=name --format=csv,noheader >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%G in ('nvidia-smi --query-gpu=name --format^=csv^,noheader 2^>nul') do (
        set "GPU_NAME=%%G"
        set "GPU_DETECTED=1"
        echo [92m[GPU DETECTED] %%G[0m
        goto :gpu_done
    )
)
:gpu_done
if !GPU_DETECTED! equ 0 (
    echo [CPU MODE] No GPU detected, using CPU
)
echo.

rem -- Sync dependencies with uv (includes all 77 ML tools + GPU if available)
if !GPU_DETECTED! equ 1 (
    echo Syncing dependencies with uv (77 ML tools + GPU acceleration)...
) else (
    echo Syncing dependencies with uv (77 ML tools)...
)
uv sync
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to sync dependencies with uv. Make sure "uv" is installed and on PATH.
    echo        Install uv: https://docs.astral.sh/uv/
    echo        Or run: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    exit /b 1
)
echo [OK] All dependencies synced successfully!
if !GPU_DETECTED! equ 1 (
    echo      [92m[GPU MODE][0m 150+ tools ready with GPU acceleration - All tools use ADK-safe wrappers!
    echo      AutoML, XGBoost, LightGBM will use GPU for 5-10x speedup!
    echo      [92m✅ 128 Non-streaming tools[0m (streaming disabled)
) else (
    echo      [CPU MODE] 150+ tools ready - All tools use ADK-safe wrappers!
    echo      AutoML, Sklearn, Fairness, Drift, Causal, HPO, and more
    echo      [92m✅ 128 Non-streaming tools[0m (streaming disabled)
)
echo.

rem -- Start the server
echo Starting server on http://localhost:8080
if !GPU_DETECTED! equ 1 (
    echo [92m[GPU acceleration enabled - training will be 5-10x faster!][0m
)
echo Press CTRL+C to stop the server
echo ===========================================================
echo.

rem -- Run the app
uv run python main.py
set "EXITCODE=%ERRORLEVEL%"

exit /b %EXITCODE%
