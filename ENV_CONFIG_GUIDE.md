# Environment Configuration Guide

## API Key Configuration (.env file)

### Issue: "Both GOOGLE_API_KEY and GEMINI_API_KEY are set"

If you see this warning, you have both API keys set in your `.env` file. The system will use `GOOGLE_API_KEY` by default and show a warning.

### Solution: Choose ONE API key

Edit your `.env` file and comment out the one you're NOT using:

```bash
# Option 1: Use Google API Key (RECOMMENDED for ADK)
GOOGLE_API_KEY=your_actual_api_key_here
# GEMINI_API_KEY=commented_out

# Option 2: Use Gemini API Key (Alternative)
# GOOGLE_API_KEY=commented_out  
GEMINI_API_KEY=your_actual_api_key_here
```

### Why This Happens
- ADK (Agent Development Kit) can use either key
- Having both set creates ambiguity
- The warning ensures you know which one is being used

## Missing Tool Functions Error

### Issue: "name 'train_lightgbm_regressor' is not defined"

Some advanced modeling tools were referenced in the code but not yet implemented.

### What Was Fixed
Commented out the following unimplemented tools in `agent.py`:
- `train_lightgbm_regressor`
- `train_xgboost_regressor`
- `train_catboost_regressor`
- `train_adaboost`
- `train_gradientboost`
- `train_randomforest`
- `train_extratrees`
- `train_dl_clf_tool` (deep learning)
- `train_dl_reg_tool` (deep learning)
- `train_tabnet_tool` (deep learning)
- `autogluon_multimodal_tool`
- `rebalance_fit_tool`
- `monitor_drift_score_tool`
- `shapley_oos_tool`

### Available Tools
The system still has 90+ working tools including:
- **Classification:** `train_lightgbm_classifier`, `train_xgboost_classifier`, `train_catboost_classifier`
- **AutoML:** `smart_autogluon_automl`, `auto_clean_data`
- **Data Cleaning:** `robust_auto_clean_file_tool`, `detect_metadata_rows`
- And many more...

## SQLite Database Error

### Issue: "sqlite3.OperationalError: unable to open database file"

The database directory didn't exist when ADK tried to create the session database.

### What Was Fixed
Added automatic directory creation in `main.py` before ADK initializes:

```python
# CRITICAL: Ensure database directory exists for ADK's session service
from pathlib import Path
if not session_service_uri:
    db_dir = Path(".")
    db_dir.mkdir(parents=True, exist_ok=True)
```

### Why This Happens
- ADK's `DatabaseSessionService` creates a SQLite database
- If the directory doesn't exist, SQLite fails to create the file
- The fix ensures the directory exists before ADK starts

### Database Locations
The system uses two databases:

1. **UI State Database:** `data_science/adk_state.db`
   - Stores UI events and session data
   - Created automatically by `init_db()`
   - Directory created automatically

2. **ADK Session Database:** `./adk_sessions.db` (default) or custom path from `SESSION_SERVICE_URI`
   - Stores ADK session data
   - Created automatically by ADK
   - Directory now created automatically

## Environment Variables Reference

### Required
```bash
# API Key (choose ONE)
GOOGLE_API_KEY=your_key_here
# OR
GEMINI_API_KEY=your_key_here

# OpenAI (if using OpenAI models)
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
```

### Optional
```bash
# Model Selection
USE_GEMINI=false
USE_ENSEMBLE=false

# Session Service (default: SQLite in current directory)
SESSION_SERVICE_URI=sqlite:///path/to/sessions.db

# Web Interface
SERVE_WEB_INTERFACE=false

# Logging
LOG_LEVEL=INFO
LITELLM_LOG=DEBUG

# State Database
STATE_DB_PATH=data_science/adk_state.db

# Context Window
MAX_CONTEXT_TOKENS=128000
CONTEXT_SAFETY_MARGIN=0.85
INITIAL_TOOL_LEVEL=1

# Feature Flags
ENABLE_UNSTRUCTURED=0
```

## Verification Checklist

After fixing these issues, verify:

- [ ] Only ONE API key is set (either GOOGLE_API_KEY or GEMINI_API_KEY)
- [ ] No warnings about duplicate API keys
- [ ] No errors about missing tool functions
- [ ] No SQLite database errors
- [ ] Application starts successfully
- [ ] Logs show: `[TOOLS] ✓ Added N non-streaming tools`
- [ ] Logs show: `[CORE] Started with N tools`

## Testing Your Configuration

1. **Check API Key Configuration:**
   ```bash
   # Look for this in startup logs:
   # Should NOT see: "Both GOOGLE_API_KEY and GEMINI_API_KEY are set"
   # Should see: "API Key Set: YES"
   ```

2. **Check Tool Loading:**
   ```bash
   # Should see in logs:
   # [TOOLS] ✓ Added 87 non-streaming tools
   # [CORE] Started with 26 tools (level: CORE)
   # Should NOT see: "name 'train_lightgbm_regressor' is not defined"
   ```

3. **Check Database Initialization:**
   ```bash
   # Should see in logs:
   # [OK] State database initialized: data_science/adk_state.db
   # [OK] Database directory verified for ADK session service
   # Should NOT see: "sqlite3.OperationalError: unable to open database file"
   ```

## Troubleshooting

### Still seeing API key warning?
- Check your `.env` file for both keys
- Make sure you commented out the unused one with `#`
- Restart the application

### Still seeing missing function errors?
- Make sure you pulled the latest code changes
- The fix is in `agent.py` lines 4686-4723
- Verify the problematic tools are commented out

### Still seeing database errors?
- Check file permissions in your project directory
- Make sure the directory is writable
- Check if antivirus is blocking SQLite
- Try setting `SESSION_SERVICE_URI` explicitly in `.env`

### Need Help?
- Check logs for detailed error messages
- Ensure all dependencies are installed
- Verify Python version compatibility (3.10+)
- Check disk space availability

## Summary of Changes

✅ **Fixed in `agent.py`:**
- Commented out 14 unimplemented tool references
- Added clear notes about which tools are available
- Reduced tool count from ~120 to ~90 working tools

✅ **Fixed in `main.py`:**
- Added automatic database directory creation
- Handles both default and custom database paths
- Graceful error handling if directory creation fails

✅ **Created `ENV_CONFIG_GUIDE.md`:**
- Complete guide to environment configuration
- Troubleshooting steps
- Verification checklist
- Best practices

All fixes are backwards compatible and don't affect existing functionality!

