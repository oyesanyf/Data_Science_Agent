# Testing CSV File Upload Fix

## Current Status

✅ **Server is running with enhanced logging**
- URL: http://localhost:8080
- Enhanced file upload callback with detailed logging
- File saves will be visible in logs

## How to Test

### Step 1: Upload a CSV File

1. Open http://localhost:8080 in your browser
2. Click the file upload button (📎) in the chat interface
3. Select any CSV file from your computer
4. The file should upload

### Step 2: Watch for These Logs

The server terminal should show:

```
INFO:data_science.agent:File upload callback triggered. Mime: text/csv, Data type: <class 'bytes'>
INFO:data_science.agent:Saving file to: C:\harfile\data_science_agent\data_science\.data\uploaded_TIMESTAMP.csv
INFO:data_science.agent:File saved successfully: C:\harfile\data_science_agent\data_science\.data\uploaded_TIMESTAMP.csv (1234 bytes)
```

### Step 3: Expected Behavior

#### ✅ SUCCESS Scenario:
```
User: [Uploads data.csv]
Agent Response: 
"[File uploaded: uploaded_1234567890.csv]
File saved to: C:\harfile\data_science_agent\data_science\.data\uploaded_1234567890.csv  
Size: 1234 bytes
Type: text/csv
The file is now available. Use list_data_files() to verify."
```

Then send a command like:
- `"list files"` → Should show the uploaded file
- `"num1 regression"` → Should auto-run AutoML
- `"clean data"` → Should auto-clean the file

#### ❌ ERROR Scenario:

If you see:
```
ERROR:data_science.agent:Error in file upload callback: ...
```

This means the file save failed. Common causes:
1. **Permission denied** - .data directory not writable
2. **Encoding error** - File contains non-UTF-8 characters
3. **Memory error** - File too large

### Step 4: Verify File Was Saved

Run this command in PowerShell:

```powershell
Get-ChildItem C:\harfile\data_science_agent\data_science\.data\
```

You should see files like:
```
uploaded_1760489084.csv
uploaded_1760489125.csv
```

## Common Issues & Fixes

### Issue 1: "LiteLlm does not support this content part"

**Cause:** Old server still running or callback not loaded  
**Fix:**
```powershell
Get-Process python | Stop-Process -Force
Start-Sleep -Seconds 2
cd C:\harfile\data_science_agent
$env:SERVE_WEB_INTERFACE='true'
uv run python main.py
```

### Issue 2: "No such file or directory: uploaded_XXXXX.csv"

**Cause:** File save failed but callback still sent the path  
**Fix:** Check the logs for ERROR messages showing why the save failed

### Issue 3: Callback not triggered at all

**Symptoms:** No "File upload callback triggered" log message  
**Possible causes:**
- Web UI is sending the file in a different format
- Mime type is not being detected as CSV
- Callback is not registered properly

**Debug:** Look for the mime type in the error message

### Issue 4: File saved but agent can't find it

**Cause:** Path mismatch between callback and tools  
**Fix:** Use `list_data_files()` to see what the agent can access

## Manual Test (If Web UI Fails)

Create a test CSV file:

```powershell
"col1,col2,col3`n1,2,3`n4,5,6" | Out-File -FilePath C:\harfile\data_science_agent\data_science\.data\test.csv -Encoding utf8
```

Then chat with the agent:
```
User: "list files"
Agent: Should show test.csv

User: "analyze test.csv"
Agent: Should load and analyze it
```

## What Changed

### Before:
- CSV upload → LiteLlm error → Complete failure
- No file saved anywhere
- Agent couldn't access uploaded data

### After:
- CSV upload → Callback intercepts → Save to disk
- Replace inline_data with text message
- Agent sees file path and can use tools
- Full logging for debugging

## Next Steps If Still Failing

1. **Check the exact error in logs** - Look for the specific exception
2. **Verify .data directory permissions** - Should be writable
3. **Test with a simple CSV** - Use the manual test above  
4. **Check mime type** - Some browsers send different mime types

## Alternative: Manual File Upload

If the automatic upload keeps failing, use the manual upload tool:

1. Chat: `"save uploaded file"`
2. Agent will use `save_uploaded_file()` tool
3. Paste your CSV content as text
4. Agent saves it manually

---

**Status:** Server running with enhanced logging  
**Ready to test:** YES  
**Documentation:** LITELLM_CSV_FIX.md has full technical details

