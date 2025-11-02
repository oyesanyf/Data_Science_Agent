# Fix Windows Environment Variable - SESSION_SERVICE_URI

## Problem Detected

Your Windows User environment variable `SESSION_SERVICE_URI` contains corrupted data:

```
sqlite:///./data_science/db/adk_sessions.db"

# Or add to .env file permanently
Add-Content .env "`nSESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db
```

This is causing SQLite database errors.

## Quick Fix - Option 1: Delete the Environment Variable (RECOMMENDED)

Run this PowerShell command **as Administrator** or in your current PowerShell:

```powershell
# Remove the corrupted environment variable (current session)
Remove-Item Env:\SESSION_SERVICE_URI -ErrorAction SilentlyContinue

# Remove from User environment variables (permanent)
[Environment]::SetEnvironmentVariable('SESSION_SERVICE_URI', $null, 'User')

# Verify it's gone
Write-Host "Current session:" $env:SESSION_SERVICE_URI
Write-Host "User env:" ([Environment]::GetEnvironmentVariable('SESSION_SERVICE_URI', 'User'))
```

**After running this, restart PowerShell and Python application!**

## Quick Fix - Option 2: Set it Correctly

If you want to keep the variable but fix it:

```powershell
# Set the correct value (no quotes, no extra text)
[Environment]::SetEnvironmentVariable('SESSION_SERVICE_URI', 'sqlite:///./data_science/db/adk_sessions.db', 'User')

# Also update current session
$env:SESSION_SERVICE_URI = 'sqlite:///./data_science/db/adk_sessions.db'

# Verify
Write-Host "Fixed value:" $env:SESSION_SERVICE_URI
```

**After running this, restart PowerShell and Python application!**

## Quick Fix - Option 3: Use GUI

1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Click "Advanced" tab
3. Click "Environment Variables" button
4. Under "User variables", find `SESSION_SERVICE_URI`
5. Either:
   - **DELETE IT** (click Delete button), OR
   - **EDIT IT** to: `sqlite:///./data_science/db/adk_sessions.db` (no quotes!)
6. Click OK on all dialogs
7. **Restart your terminal and application**

## Why This Happened

Someone ran a PowerShell command that **set** the environment variable incorrectly, possibly:

```powershell
# This is WRONG - it puts the entire command as the value:
$env:SESSION_SERVICE_URI = @"
sqlite:///./data_science/db/adk_sessions.db"

# Or add to .env file permanently
Add-Content .env "`nSESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db
"@
```

The correct way is:
```powershell
$env:SESSION_SERVICE_URI = 'sqlite:///./data_science/db/adk_sessions.db'
```

## What the Code Fix Does

The fix I added to `main.py` (lines 274-285) **automatically cleans** corrupted values:
- ✅ Strips quotes
- ✅ Removes newlines and extra text  
- ✅ Falls back to default if empty

**So even with the corrupted variable, your app should work now!**

But it's still better to fix the environment variable properly.

## After You Fix It

Test that it's clean:

```powershell
# Check current session
$env:SESSION_SERVICE_URI

# Should output EITHER:
# sqlite:///./data_science/db/adk_sessions.db
# OR
# (nothing - if you deleted it, which is fine!)
```

Then restart your application:

```bash
python main.py
```

You should see:
```
[INFO] Using session service: sqlite:///./data_science/db/adk_sessions.db
[OK] Created database directory: C:\harfile\data_science_agent\data_science\db
```

## Environment Variable Priority

When Python's `os.getenv()` looks for a variable, it checks:
1. **Current session** (`$env:VAR`)
2. **User environment variables** (permanent)
3. **System environment variables** (permanent)
4. **`.env` file** (if using python-dotenv)

Your issue is in **User environment variables** (#2), which takes priority over the `.env` file.

## Recommendation

**Delete the Windows environment variable entirely** and let the code use defaults or the `.env` file. This gives you more flexibility and avoids system-wide pollution.

```powershell
# Clean slate approach
[Environment]::SetEnvironmentVariable('SESSION_SERVICE_URI', $null, 'User')
Remove-Item Env:\SESSION_SERVICE_URI -ErrorAction SilentlyContinue
```

Then if you need to set it, use the `.env` file instead:
```bash
SESSION_SERVICE_URI=sqlite:///./data_science/db/adk_sessions.db
```

