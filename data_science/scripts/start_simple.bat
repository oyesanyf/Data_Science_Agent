@echo off
REM Simple Data Science Agent Startup (No checks)
REM Quick start for when you know everything is already set up

set SERVE_WEB_INTERFACE=true
echo Starting Data Science Agent on http://localhost:8080
echo Press CTRL+C to stop the server
echo.
uv run python main.py

