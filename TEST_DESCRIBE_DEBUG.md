# Debug: Why describe_tool_guard Shows No Results

## Issue

UI shows:
```
### describe_tool_guard @ 2025-10-28 14:31:40
## Result
Tool completed with status: **success**
_Last updated 2025-10-28 14:31:40_
```

**No actual data!**

## Investigation

### What describe_tool_guard Does (Correctly)

Looking at `head_describe_guard.py`:

1. ✅ Line 334-361: Creates formatted message with statistics
2. ✅ Line 365-381: Sets ALL display fields (`__display__`, `message`, `ui_text`, etc.)
3. ✅ Line 393-422: Saves markdown artifact
4. ✅ Line 460: Returns result with all fields

**The guard is doing everything right!**

### The Real Problem

Line 336-347 is the key:
```python
if "overview" in result:
    # Format overview data
    message_parts.append(json.dumps(overview, indent=2))
```

**If `result["overview"]` is EMPTY or doesn't exist, then formatted_message will be just the header!**

### Root Cause

The underlying `describe_tool()` is returning:
```python
{
    "status": "success",
    # BUT NO ACTUAL DATA:
    # "overview": None or missing
    # "shape": None or missing
    # "columns": None or missing
}
```

### Why This Happens

1. **File not found** - csv_path doesn't resolve to actual file
2. **File not bound** - dataset not properly uploaded/registered in state
3. **describe() function fails silently** - Returns success but no data

## Diagnostic Steps

### Check What Data describe() Is Getting

Add this at the start of describe_tool_guard:
```python
logger.error(f"[DESCRIBE DEBUG] csv_path = {csv_path}")
logger.error(f"[DESCRIBE DEBUG] File exists? {Path(csv_path).exists() if csv_path else False}")
logger.error(f"[DESCRIBE DEBUG] File size: {Path(csv_path).stat().st_size if csv_path and Path(csv_path).exists() else 0}")
```

### Check What describe() Returns

After calling describe_tool:
```python
logger.error(f"[DESCRIBE DEBUG] Result keys: {list(result.keys())}")
logger.error(f"[DESCRIBE DEBUG] Has overview? {'overview' in result}")
logger.error(f"[DESCRIBE DEBUG] Overview value: {result.get('overview', 'MISSING')}")
```

### Check If File Is Uploaded

In agent conversation, ask user:
```
"Have you uploaded a file? I don't see any data loaded yet.
Try: list_data_files() to see available files"
```

## Most Likely Cause

**FILE NOT UPLOADED YET**

The user probably:
1. Started the agent
2. Ran `analyze_dataset()` without uploading a file first
3. Tools return "success" but process nothing (graceful degradation)

## Solution

The agent should **detect when no file is available** and tell the user:

```python
# In describe_tool_guard, before calling describe:
if not csv_path:
    # Check state for uploaded file
    state = getattr(tool_context, "state", {})
    default_csv = state.get("default_csv_path")
    
    if not default_csv:
        return {
            "status": "warning",
            "message": """
❌ **No dataset found!**

Please upload a CSV file first:
1. Click "Upload File" button
2. Select your dataset
3. Then run describe() again

Or specify a file path:
`describe(csv_path="your_file.csv")`
            """
        }
```

## Quick Fix

Add explicit empty data detection in describe_tool_guard:

```python
# After line 332, add:
if not result.get("overview") and not result.get("shape"):
    logger.warning("[DESCRIBE GUARD] NO DATA returned from describe!")
    return {
        "status": "warning",
        "__display__": """
❌ **No statistics generated**

Possible reasons:
- No file uploaded yet
- File path not found
- Dataset is empty

**Next steps:**
1. Upload a CSV file
2. Or run: list_data_files()
3. Then try: describe() again
        """,
        "message": "No data found - please upload a file first"
    }
```

## Test This Theory

Ask the user:
```
"Can you check your browser console and look for any errors?
Also, did you upload a CSV file before running analyze_dataset()?"
```

If they say "no file uploaded", that's the issue!

---

**Status:** Needs user confirmation
**Most likely:** File not uploaded yet
**Fix:** Add better error messages when no data is available

