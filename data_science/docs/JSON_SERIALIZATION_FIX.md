# ✅ JSON Serialization Fix - "Error Formatting Output"

## Problem

Multiple tools were showing:
```
✅ tool_name completed (error formatting output)
```

**Affected Tools:**
- `analyze_dataset_tool`
- `shape_tool`

**Working Tools (used as reference):**
- `describe_tool_guard` ✅

## Root Cause

The callback's `after_tool_callback` function (in `callbacks.py` line 438) attempts to JSON-serialize the entire result dictionary:

```python
json.dumps(result, default=str)
```

If this fails, it catches the exception (line 443) and returns:
```python
"__display__": f"✅ **{tool_name}** completed (error formatting output)"
```

**Why it was failing:**
1. Tool functions were returning dicts with **non-JSON-serializable objects**:
   - Pandas DataFrames
   - Numpy arrays
   - Complex Python objects in `column_names` (datetime, categorical types, etc.)

2. Even though display fields (`__display__`, `message`, etc.) were strings, the **ENTIRE dict** had to be JSON-serializable, including all internal fields.

3. When `_ensure_ui_display` tried to process these dicts, the JSON roundtrip test failed.

## Solution

### Fix 1: Create Clean Result Dicts (analyze_dataset_tool)

**File:** `data_science/adk_safe_wrappers.py`  
**Lines:** 1893-1913, 1919-1928, 1955-1964

**Strategy:** Instead of modifying the original result dict (which contains DataFrames, arrays, etc.), create a **NEW clean dict** with only JSON-serializable fields.

**Before:**
```python
# Modifying original result (contains DataFrames, arrays, etc.)
result["__display__"] = loud_message
result["message"] = loud_message
# ... etc
return result  # Still contains non-serializable objects!
```

**After:**
```python
# Create CLEAN result dict with only serializable fields
clean_result = {
    "status": result.get("status", "success"),
    "__display__": loud_message,
    "message": loud_message,
    "text": loud_message,
    "ui_text": loud_message,
    "content": loud_message,
    "display": loud_message,
    "_formatted_output": loud_message,
}

# Safely add artifacts if serializable
if "artifacts" in result:
    try:
        import json
        json.dumps(result["artifacts"])
        clean_result["artifacts"] = result["artifacts"]
    except:
        clean_result["artifacts"] = [str(a) for a in result["artifacts"]] if isinstance(result["artifacts"], list) else [str(result["artifacts"])]

result = clean_result  # Replace with clean dict
return result
```

**Key Changes:**
1. **Lines 1893-1913**: When combining head/describe results, create clean dict
2. **Lines 1919-1928**: Fallback case creates clean dict
3. **Lines 1955-1964**: Error case creates clean dict

### Fix 2: Convert Column Names to Strings (shape_tool)

**File:** `data_science/ds_tools.py`  
**Lines:** 447, 489

**Strategy:** Convert `column_names` to strings since DataFrame columns can be datetime, categorical, or other complex types that don't serialize to JSON.

**Before:**
```python
"column_names": columns,  # columns = list(df.columns)
```

**After:**
```python
"column_names": [str(col) for col in columns],  # Convert to strings for JSON serialization
```

**Also Fixed:**
Markdown generation (line 447) to ensure column names are strings:
```python
{chr(10).join(f'- {str(col)}' for col in columns[:50])}
```

## Why This Works

1. **Clean Dicts:** The callback can successfully serialize clean dicts because they only contain:
   - Primitive types (str, int, float, bool)
   - Simple collections (list of strings)
   - No DataFrames, numpy arrays, or complex objects

2. **String Conversion:** Column names as strings are always JSON-serializable, regardless of their original type.

3. **Artifact Safety:** Artifacts are checked for serializability before adding, with fallback to string conversion.

## Pattern for Other Tools

If any tool shows "error formatting output", apply this pattern:

```python
def my_tool(...):
    # Get result from underlying function
    result = underlying_function(...)
    
    # Create CLEAN result dict with only serializable fields
    clean_result = {
        "status": "success",
        "__display__": formatted_message,
        "message": formatted_message,
        "text": formatted_message,
        "ui_text": formatted_message,
        "content": formatted_message,
        "display": formatted_message,
        "_formatted_output": formatted_message,
    }
    
    # Add other fields only if they're serializable
    if "artifacts" in result:
        try:
            json.dumps(result["artifacts"])
            clean_result["artifacts"] = result["artifacts"]
        except:
            clean_result["artifacts"] = [str(a) for a in result["artifacts"]]
    
    return clean_result
```

## Testing

After restart, test with:

```python
# Upload a CSV, then:
analyze_dataset()  # Should show full analysis with head + describe
shape()            # Should show dimensions and column names
```

**Expected Output:**
```
📊 **Dataset Analysis Complete!**

[Dataset statistics]
[First 5 rows preview]
[Descriptive statistics]

✅ **Ready for next steps**
```

No more "error formatting output" messages!

## Files Modified

1. **`data_science/adk_safe_wrappers.py`**
   - Lines 1893-1913: Clean result creation for success case
   - Lines 1919-1928: Clean result creation for fallback case
   - Lines 1955-1964: Clean result creation for error case

2. **`data_science/ds_tools.py`**
   - Line 447: Convert column names to strings in markdown
   - Line 489: Convert column names to strings in result dict

## Related Files

- `data_science/callbacks.py` (Lines 437-452): JSON serialization logic
- `data_science/head_describe_guard.py`: Working example (describe_tool_guard)

---

**Status:** Fixed  
**Date:** October 24, 2025  
**Issue:** JSON serialization error in callback  
**Solution:** Create clean result dicts with only JSON-serializable fields

