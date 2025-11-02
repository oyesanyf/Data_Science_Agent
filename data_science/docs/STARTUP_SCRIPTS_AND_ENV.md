# Do All Startup Scripts Load .env?

## Short Answer: YES ✅

All startup scripts eventually load `.env` because they all call `main.py`, which loads `.env` automatically.

---

## How It Works

### Step 1: All Scripts Call main.py

| Script | How It Runs main.py |
|--------|-------------------|
| `start_server.py` | Calls `main.py` directly |
| `start_server.ps1` | Runs `uv run python main.py` |
| `start_server.bat` | Runs `uv run python main.py` |
| `start_with_openai.ps1` | Runs `uv run python main.py` |
| `start_with_validation.ps1` | Runs `uv run python main.py` |

### Step 2: main.py Loads .env Automatically

```python
# File: main.py (line 188 & 197)
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
```

**Result**: `.env` is ALWAYS loaded, regardless of which startup script you use!

---

## Startup Scripts Breakdown

### 1. start_server.py (Python)
```python
# Calls main.py after setup
import main
```
✅ Loads .env (via main.py)

### 2. start_server.ps1 (PowerShell)
```powershell
# Line 84
uv run python main.py
```
✅ Loads .env (via main.py)

### 3. start_server.bat (Windows Batch)
```batch
# Line 132
uv run python main.py
```
✅ Loads .env (via main.py)

### 4. start_with_openai.ps1 (Setup Helper)
```powershell
# Lines 10-39: Creates .env if missing
if (-not (Test-Path ".env")) {
    # Prompts for API key
    # Creates .env file
}

# Line 47: Runs main.py
uv run python main.py
```
✅ Creates .env if needed, then loads it (via main.py)

### 5. start_with_validation.ps1
```powershell
# Similar to start_server.ps1
uv run python main.py
```
✅ Loads .env (via main.py)

---

## Load Order

```
You run: python start_server.py (or any startup script)
    ↓
Startup script sets up environment (clears cache, checks GPU, etc.)
    ↓
Startup script calls: python main.py
    ↓
main.py line 197: load_dotenv()  ← .env LOADED HERE
    ↓
main.py reads environment variables (OPENAI_API_KEY, USE_ENSEMBLE, etc.)
    ↓
Server starts with your configuration
```

---

## What This Means

### ✅ You Can Use .env With ANY Startup Script

No matter which script you use, your `.env` file will be loaded:

```bash
# All of these load .env automatically:
python start_server.py
.\start_server.ps1
.\start_server.bat
.\start_with_openai.ps1
```

### ✅ Environment Variables Work From Multiple Sources

The load order (last wins):
1. System environment variables
2. `.env` file (loaded by main.py)
3. Variables set in terminal before running script

**Example:**
```powershell
# In .env file:
OPENAI_MODEL=gpt-5

# In terminal:
$env:OPENAI_MODEL = "gpt-5-mini"

# Result: Uses gpt-5-mini (terminal overrides .env)
```

---

## Special Case: start_with_openai.ps1

This script is unique - it **creates** a `.env` file if one doesn't exist:

```powershell
# Prompts you for:
# - OpenAI API key
# - Creates .env with sensible defaults

# Then runs main.py (which loads the .env it just created)
```

**Use this for first-time setup!**

---

## Verification

### Check if .env is loaded:

1. Create `.env`:
```bash
OPENAI_API_KEY=sk-test-key
USE_ENSEMBLE=true
OPENAI_MODEL=gpt-5
```

2. Start server:
```powershell
python start_server.py
```

3. Look for log messages:
```
[OK] Using OpenAI (Gemini disabled)
# OR
🎯 ENSEMBLE MODE ACTIVE: gpt-5 + gemini-2.0-flash-exp
```

If you see these, `.env` was loaded successfully!

---

## Troubleshooting

### Problem: "API key not found"
**Cause**: `.env` file not in the right location or has wrong format

**Solution**:
```powershell
# 1. Check .env exists in project root
Test-Path .env

# 2. Check format (no quotes around values)
# ✅ Correct:
OPENAI_API_KEY=sk-123456789

# ❌ Wrong:
OPENAI_API_KEY="sk-123456789"
```

### Problem: "Environment variable not recognized"
**Cause**: Typo in variable name or .env not being read

**Solution**:
```powershell
# Verify main.py loads dotenv
Select-String -Path main.py -Pattern "load_dotenv"

# Should show:
# main.py:197:load_dotenv()
```

---

## Summary Table

| Startup Script | Creates .env? | Loads .env? | Calls main.py? |
|---------------|--------------|-------------|----------------|
| start_server.py | ❌ No | ✅ Yes (via main.py) | ✅ Yes |
| start_server.ps1 | ❌ No | ✅ Yes (via main.py) | ✅ Yes |
| start_server.bat | ❌ No | ✅ Yes (via main.py) | ✅ Yes |
| start_with_openai.ps1 | ✅ Yes (if missing) | ✅ Yes (via main.py) | ✅ Yes |
| start_with_validation.ps1 | ❌ No | ✅ Yes (via main.py) | ✅ Yes |
| **main.py** | ❌ No | ✅ **YES** (line 197) | N/A (is main) |

---

## Best Practice

### For First-Time Setup:
```powershell
.\start_with_openai.ps1
# Creates .env and starts server
```

### For Regular Use:
```powershell
# Edit .env once:
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
USE_ENSEMBLE=true

# Then just run:
python start_server.py
# OR
.\start_server.ps1
```

---

## Conclusion

✅ **YES** - All startup scripts load `.env`
✅ Loaded automatically by `main.py` (line 197)
✅ Works with any startup script
✅ No need to set environment variables manually

**Just create a `.env` file and you're done!**

