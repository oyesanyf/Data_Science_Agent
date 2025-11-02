# 🔧 How to Set Environment Variables

Environment variables are **NOT** set in the startup scripts. You must set them yourself before starting the server.

## Quick Answer

Environment variables are set in **YOUR TERMINAL/SHELL** before running the server.

---

## Option 1: PowerShell (Recommended for Windows)

### Temporary (Current Session Only):

```powershell
# Set API keys
$env:OPENAI_API_KEY = "sk-your-key-here"
$env:GOOGLE_API_KEY = "your-gemini-key-here"

# Enable ensemble mode
$env:USE_ENSEMBLE = "true"

# Optional: Choose models
$env:OPENAI_MODEL = "gpt-5"
$env:GENAI_MODEL = "gemini-2.0-flash-exp"

# Now start server
python start_server.py
```

### Permanent (All Sessions):

```powershell
# Set permanently (survives restarts)
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-your-key-here", "User")
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "your-gemini-key-here", "User")
[System.Environment]::SetEnvironmentVariable("USE_ENSEMBLE", "true", "User")

# Restart PowerShell, then:
python start_server.py
```

---

## Option 2: Create a `.env` File

Create a file named `.env` in the project root (`C:\harfile\data_science_agent\.env`):

```bash
# API Keys
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-gemini-key-here

# Ensemble Mode
USE_ENSEMBLE=true

# Model Selection
OPENAI_MODEL=gpt-5
GENAI_MODEL=gemini-2.0-flash-exp

# Optional Settings
LITELLM_MAX_RETRIES=4
LITELLM_TIMEOUT_SECONDS=60
```

**Important**: The code already loads `.env` files automatically (via `python-dotenv`), so just create this file and restart!

---

## Option 3: Windows Environment Variables GUI

1. Press `Win + X`, select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", click "New"
5. Add each variable:
   - Name: `OPENAI_API_KEY`, Value: `sk-...`
   - Name: `GOOGLE_API_KEY`, Value: `your-gemini-key`
   - Name: `USE_ENSEMBLE`, Value: `true`
6. Click "OK" to save
7. **Restart PowerShell** to load new variables
8. Run `python start_server.py`

---

## Option 4: Batch Script (Windows)

Create `set_env_and_start.bat`:

```batch
@echo off
set OPENAI_API_KEY=sk-your-key-here
set GOOGLE_API_KEY=your-gemini-key-here
set USE_ENSEMBLE=true
set OPENAI_MODEL=gpt-5
set GENAI_MODEL=gemini-2.0-flash-exp

echo ============================================================
echo Starting with Ensemble Mode
echo OpenAI: %OPENAI_MODEL%
echo Gemini: %GENAI_MODEL%
echo ============================================================

python start_server.py
```

Then run: `.\set_env_and_start.bat`

---

## Option 5: PowerShell Script

Create `set_env_and_start.ps1`:

```powershell
# Set environment variables
$env:OPENAI_API_KEY = "sk-your-key-here"
$env:GOOGLE_API_KEY = "your-gemini-key-here"
$env:USE_ENSEMBLE = "true"
$env:OPENAI_MODEL = "gpt-5"
$env:GENAI_MODEL = "gemini-2.0-flash-exp"

Write-Host "============================================================" -ForegroundColor Green
Write-Host "Starting with Ensemble Mode" -ForegroundColor Green
Write-Host "OpenAI: $env:OPENAI_MODEL" -ForegroundColor Cyan
Write-Host "Gemini: $env:GENAI_MODEL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Green

# Start server
python start_server.py
```

Then run: `.\set_env_and_start.ps1`

---

## Verify Environment Variables Are Set

### PowerShell:
```powershell
# Check if variables are set
$env:OPENAI_API_KEY
$env:GOOGLE_API_KEY
$env:USE_ENSEMBLE

# Should show your values (not empty)
```

### In Python (while server is running):
```python
import os
print("OpenAI Key:", os.getenv("OPENAI_API_KEY")[:10] + "..." if os.getenv("OPENAI_API_KEY") else "NOT SET")
print("Google Key:", os.getenv("GOOGLE_API_KEY")[:10] + "..." if os.getenv("GOOGLE_API_KEY") else "NOT SET")
print("Ensemble:", os.getenv("USE_ENSEMBLE", "false"))
```

---

## Common Mistakes

### ❌ Wrong: Setting in startup scripts
```powershell
# DON'T edit start_server.ps1 to add:
$env:OPENAI_API_KEY = "sk-..."  # Wrong place!
```

### ✅ Right: Set before running
```powershell
# In your terminal first:
$env:OPENAI_API_KEY = "sk-..."
$env:GOOGLE_API_KEY = "your-key"
$env:USE_ENSEMBLE = "true"

# Then run:
python start_server.py
```

---

## All Available Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *none* | **Required** - OpenAI API key |
| `GOOGLE_API_KEY` | *none* | For Gemini (required if USE_ENSEMBLE=true) |
| `USE_ENSEMBLE` | `false` | Enable multi-agent voting |
| `OPENAI_MODEL` | `gpt-5` | OpenAI model to use |
| `GENAI_MODEL` | `gemini-2.0-flash-exp` | Gemini model to use |
| `LITELLM_MAX_RETRIES` | `4` | Max retry attempts |
| `LITELLM_TIMEOUT_SECONDS` | `60` | Request timeout |
| `MAX_CONTEXT_TOKENS` | `128000` | Context window limit |
| `CONTEXT_SAFETY_MARGIN` | `0.85` | Safety margin for context |
| `SERVE_WEB_INTERFACE` | Set by script | Enable web UI |

---

## Recommended Setup (Best Practice)

### 1. Create `.env` file:
```bash
# File: .env (in project root)
OPENAI_API_KEY=sk-your-actual-key-here
GOOGLE_API_KEY=your-gemini-key-here
USE_ENSEMBLE=true
OPENAI_MODEL=gpt-5
GENAI_MODEL=gemini-2.0-flash-exp
```

### 2. Add to `.gitignore`:
```bash
# Make sure .env is in .gitignore (so you don't commit secrets)
echo ".env" >> .gitignore
```

### 3. Start server:
```powershell
python start_server.py
```

**That's it!** The code automatically loads `.env` files.

---

## Quick Test

```powershell
# 1. Set environment variables
$env:OPENAI_API_KEY = "sk-..."
$env:GOOGLE_API_KEY = "gemini-..."
$env:USE_ENSEMBLE = "true"

# 2. Verify they're set
Write-Host "OpenAI Key: $($env:OPENAI_API_KEY.Substring(0,10))..."
Write-Host "Google Key: $($env:GOOGLE_API_KEY.Substring(0,10))..."
Write-Host "Ensemble: $env:USE_ENSEMBLE"

# 3. Start server
python start_server.py
```

---

## Where Are They Read?

The code reads environment variables in `data_science/agent.py`:

```python
# Line 2235: Check if ensemble enabled
use_ensemble = os.getenv("USE_ENSEMBLE", "false").lower() in ("true", "1", "yes")

# Line 2241: Read model names
openai_model_name = os.getenv("OPENAI_MODEL", "gpt-5")
gemini_model_name = os.getenv("GENAI_MODEL", "gemini-2.0-flash-exp")

# Lines 2478-2479: Check API keys
has_openai = os.getenv("OPENAI_API_KEY")
has_gemini = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
```

---

## Summary

✅ **Easiest**: Create `.env` file in project root
✅ **Fastest**: Set in PowerShell before running
✅ **Permanent**: Use Windows Environment Variables GUI
✅ **Scriptable**: Create custom startup script

**The code does NOT set these variables - YOU must set them!**

