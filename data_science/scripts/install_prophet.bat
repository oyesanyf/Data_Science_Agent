@echo off
echo ============================================================
echo Installing Prophet (Time Series Forecasting)
echo ============================================================
echo.
echo Prophet requires special installation on Windows...
echo This will install: pystan, prophet, and dependencies
echo.

echo Step 1: Installing pystan first...
uv pip install pystan>=3.0.0
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] pystan installation failed. Trying alternative method...
    uv pip install pystan==2.19.1.1
)

echo.
echo Step 2: Installing prophet...
uv pip install prophet>=1.1.0
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Prophet installation failed!
    echo.
    echo SOLUTION 1 - Use conda (recommended for Windows):
    echo   conda install -c conda-forge prophet
    echo.
    echo SOLUTION 2 - Use pre-built wheels:
    echo   pip install prophet --prefer-binary
    echo.
    echo SOLUTION 3 - Manual wheel installation:
    echo   Download from: https://github.com/facebook/prophet/releases
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Prophet is now installed.
echo ============================================================
echo.
echo Test it by running:
echo   python -c "import prophet; print('Prophet version:', prophet.__version__)"
echo.
pause

