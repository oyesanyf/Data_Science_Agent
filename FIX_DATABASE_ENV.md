# Fix Database Error - .env File Issue

## Problem Detected

Your `.env` file has corrupted `SESSION_SERVICE_URI` value with extra text:

```
SESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db"\n\n# Or add to .env file permanently\nAdd-Content .env...
```

This causes SQLite to fail when trying to open the database.

## Quick Fix

### Option 1: Remove the problematic line from .env

1. Open `.env` file in your text editor
2. Find the line starting with `SESSION_SERVICE_URI`
3. **Delete the entire line** (or comment it out with `#`)
4. Save the file

The system will use the default location automatically.

### Option 2: Fix the .env value

1. Open `.env` file
2. Replace the corrupted line with this **exact** line:

```bash
SESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db
```

**Important:** No quotes, no extra text, no newlines!

### Option 3: Use PowerShell to fix it

Run these commands:

```powershell
# Backup current .env
Copy-Item .env .env.backup

# Remove the corrupted line
(Get-Content .env) | Where-Object { $_ -notmatch '^SESSION_SERVICE_URI' } | Set-Content .env.temp
Move-Item .env.temp .env -Force

# Add the correct line
Add-Content .env "SESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db"

echo "Fixed! Restart your application."
```

## What I Fixed in the Code

I added automatic cleanup in `main.py` (lines 274-285) that:
- ✅ Strips quotes from the URI
- ✅ Removes newlines and extra text
- ✅ Cleans up corrupted values
- ✅ Falls back to default if cleaning fails

And enhanced directory creation (lines 319-351) to:
- ✅ Handle `./` prefixes correctly
- ✅ Create nested directories (data_science/db/)
- ✅ Work with both absolute and relative paths
- ✅ Provide better error messages

## Verify the Fix

After fixing your `.env` file, test it:

```powershell
# Check the value is clean
python -c "import os; print('URI:', repr(os.getenv('SESSION_SERVICE_URI')))"

# Should output:
# URI: 'sqlite:///./data_science/db/adk_sessions.db'
# OR
# URI: None  (if you removed it - this is fine!)
```

## Understanding the Error

The error:
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

Was caused by:
1. ❌ Corrupted `SESSION_SERVICE_URI` value in `.env`
2. ❌ SQLite tried to create a file with invalid path
3. ❌ File creation failed

Now fixed by:
1. ✅ Automatic value cleanup
2. ✅ Proper directory creation
3. ✅ Better error handling

## Test Your Application

```bash
python main.py
```

You should now see:
```
[INFO] Using session service: sqlite:///./data_science/db/adk_sessions.db
[OK] Created database directory: C:\harfile\data_science_agent\data_science\db
[OK] State database initialized for UI sink
```

Instead of the SQLite error!

## Why This Happened

It looks like someone tried to copy a PowerShell command example into the `.env` file:

```powershell
Add-Content .env "`nSESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db"
```

This is a **command to SET the variable**, not the variable value itself.

The `.env` file should only contain:
```bash
SESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db
```

No quotes, no commands, just the key=value pair!

## Recommended .env Format

Here's what your `.env` file should look like:

```bash
# API Keys (choose ONE)
GOOGLE_API_KEY=your_key_here
# GEMINI_API_KEY=your_key_here

# OpenAI
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o

# Database (optional - system will use default if not set)
SESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db

# Logging
LOG_LEVEL=INFO

# Feature flags
ENABLE_UNSTRUCTURED=0
```

Clean, simple, one setting per line!

