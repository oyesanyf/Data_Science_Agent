# Auto-Install Dependencies Feature

## Overview

The Data Science Agent now includes **automatic dependency checking and installation** at startup. This ensures all required packages are available before the server starts, preventing import errors like "No module named 'litellm'".

## How It Works

### 1. Automatic Dependency Check

When you start the server, it automatically:
- ✅ Checks for all critical dependencies (litellm, openai, pandas, numpy, etc.)
- 📦 Installs any missing packages automatically
- 🚀 Starts the server only when all dependencies are ready

### 2. Startup Methods

#### **Method 1: Using the Startup Script (Recommended)**

Simply run:
```powershell
.\start_server.ps1
```

This script:
- Kills any existing server on port 8080
- Syncs all dependencies using `uv`
- Enables the web interface automatically
- Checks and installs missing packages
- Starts the server

#### **Method 2: Using uv run Directly**

```powershell
$env:SERVE_WEB_INTERFACE="true"
uv run python main.py
```

#### **Method 3: Manual Python**

```powershell
uv sync
uv run python main.py
```

## What Gets Checked

The following critical packages are automatically verified:
- `litellm` - LLM integration
- `openai` - OpenAI API client
- `python-dotenv` - Environment variable management
- `uvicorn` - ASGI server
- `fastapi` - Web framework
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `scikit-learn` - Machine learning

## Server Configuration

### Enable Web Interface

The web interface is **disabled by default**. To enable it:

**Option 1: Use the startup script** (automatically enables it)
```powershell
.\start_server.ps1
```

**Option 2: Set environment variable manually**
```powershell
$env:SERVE_WEB_INTERFACE="true"
uv run python main.py
```

**Option 3: Create a .env file**
```
SERVE_WEB_INTERFACE=true
OPENAI_API_KEY=your_api_key_here
```

## Troubleshooting

### Issue: "Port 8080 already in use"

**Solution:** Use the startup script - it automatically kills existing processes:
```powershell
.\start_server.ps1
```

Or manually kill the process:
```powershell
# Find the process
netstat -ano | findstr :8080

# Kill it (replace PID with actual process ID)
taskkill /F /PID <PID>
```

### Issue: "No module named 'litellm'"

**Solution:** This should no longer happen! The auto-install feature handles it. If you still see this:
1. Make sure you're using `uv run python main.py`
2. Or run `uv sync` first
3. The auto-install function in `main.py` will install it automatically

### Issue: Dependencies not installing

**Solution:** 
1. Ensure you have `uv` installed
2. Or the system will fall back to `pip`
3. Check your internet connection

## Example Output

When starting the server, you'll see:

```
============================================================
CHECKING DEPENDENCIES...
============================================================
✓ litellm              - OK
✓ openai               - OK
✓ dotenv               - OK
✓ uvicorn              - OK
✓ fastapi              - OK
✓ pandas               - OK
✓ numpy                - OK
✓ sklearn              - OK

✓ All dependencies are already installed!

============================================================
DATA SCIENCE AGENT - VERBOSE LOGGING ENABLED
============================================================
Log Level: INFO
LiteLLM Logging: ENABLED
OpenAI Model: gpt-4o
API Key Set: YES
============================================================
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

## Access the Server

Once running, access the web interface at:
```
http://localhost:8080
```

## API Documentation

View the API documentation at:
```
http://localhost:8080/docs
```

## Notes

- The server uses the `.venv` virtual environment managed by `uv`
- All dependencies are defined in `pyproject.toml`
- Sessions are stored in memory by default (lost on restart)
- Set `SESSION_SERVICE_URI` environment variable for persistent sessions

