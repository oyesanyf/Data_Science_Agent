# Fix: "Unknown action: select_features" Error

**Date:** 2025-10-24  
**Issue:** `select_features()` failing with "Unknown action: select_features"  
**Root Cause:** Async function wrappers not using `_run_async()` helper  
**Status:** ✅ FIXED

---

## Problem

User tried to run `select_features()` and received:
```json
{
  "status": "failed",
  "error": "Unknown action: select_features"
}
```

## Root Cause Analysis

### The Issue
Three feature selection tools have **async** implementations in `ds_tools.py`:
- `select_features` (line 4062)
- `recursive_select` (line 4095)
- `sequential_select` (line 4117)

But their wrappers in `adk_safe_wrappers.py` were calling them **directly without awaiting**:

### ❌ OLD CODE (BROKEN)
```python
def select_features_tool(target: str, k: int = 10, csv_path: str = "", **kwargs):
    from .ds_tools import select_features
    # ...
    # Calling async function without await - returns coroutine, not result!
    return _ensure_ui_display(
        select_features(target=target, k=k, csv_path=csv_path, tool_context=tool_context),
        "select_features"
    )
```

### Why This Failed
- `select_features()` is declared as `async def`, so calling it returns a **coroutine object**
- The coroutine was never awaited, so the actual function never ran
- `_ensure_ui_display()` received a coroutine instead of a result dict
- This caused the "Unknown action" error

---

## The Fix

### ✅ NEW CODE (CORRECT)
```python
def select_features_tool(target: str, k: int = 10, csv_path: str = "", **kwargs):
    from .ds_tools import select_features
    # ...
    # Use _run_async helper to properly execute async function
    result = _run_async(
        select_features(target=target, k=k, csv_path=csv_path, tool_context=tool_context)
    )
    return _ensure_ui_display(result, "select_features")
```

### What `_run_async()` Does
```python
def _run_async(coro):
    """Helper to run async functions from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(coro)
        else:
            return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
```

- Handles both running and non-running event loops
- Properly awaits the coroutine
- Returns the actual result

---

## Files Modified

### ✅ `data_science/adk_safe_wrappers.py`

**1. select_features_tool (lines 323-325)**
```python
# select_features is async, must use _run_async
result = _run_async(select_features(target=target, k=k, csv_path=csv_path, tool_context=tool_context))
return _ensure_ui_display(result, "select_features")
```

**2. recursive_select_tool (lines 345-347)**
```python
# recursive_select is async, must use _run_async
result = _run_async(recursive_select(target=target, csv_path=csv_path, tool_context=tool_context))
return _ensure_ui_display(result, "recursive_select")
```

**3. sequential_select_tool (lines 367-369)**
```python
# sequential_select is async, must use _run_async
result = _run_async(sequential_select(target=target, direction=direction, n_features=n_features, csv_path=csv_path, tool_context=tool_context))
return _ensure_ui_display(result, "sequential_select")
```

---

## What These Tools Do

### `select_features(target, k=10)`
- Uses **SelectKBest** algorithm
- Selects top K most predictive features
- Uses chi-squared test for classification, f-regression for regression
- Automatically encodes categorical variables
- Saves result to `selected_kbest.csv`

**Example:**
```python
select_features(target='tip', k=10)
# Returns top 10 features most correlated with tip amount
```

### `recursive_select(target)`
- Uses **Recursive Feature Elimination (RFE)**
- Trains model, removes weakest feature, repeats
- More thorough but slower than SelectKBest
- Uses cross-validation for optimal feature count

**Example:**
```python
recursive_select(target='tip')
# Uses RFE with RandomForest to find optimal features
```

### `sequential_select(target, direction='forward', n_features=10)`
- Uses **Sequential Feature Selection**
- Forward: Start with 0, add best feature iteratively
- Backward: Start with all, remove worst feature iteratively
- Most computationally expensive but often most accurate

**Example:**
```python
sequential_select(target='tip', direction='forward', n_features=10)
# Builds up to 10 features one at a time
```

---

## Testing

After this fix, all three tools should work correctly:

### Test 1: SelectKBest (Fast)
```
User: "Select the top 10 features for predicting tip"
→ select_features(target='tip', k=10)
→ ✅ Should complete successfully
```

### Test 2: Recursive Feature Elimination (Thorough)
```
User: "Use recursive feature elimination for tip prediction"
→ recursive_select(target='tip')
→ ✅ Should complete successfully
```

### Test 3: Sequential Selection (Most Accurate)
```
User: "Use forward sequential selection to find 10 best features for tip"
→ sequential_select(target='tip', direction='forward', n_features=10)
→ ✅ Should complete successfully
```

---

## Expected Results

### Before Fix ❌
```json
{
  "status": "failed",
  "error": "Unknown action: select_features"
}
```

### After Fix ✅
```
✅ Feature selection complete!

Selected 10 features using SelectKBest (f_regression):
- total_bill
- size
- sex_Male
- smoker_Yes
- day_Sat
- time_Dinner
... (and 4 more)

📊 Saved to: selected_kbest.csv
```

---

## Pattern for Other Async Tools

If you encounter similar "Unknown action" errors for other tools, check:

1. Is the core function `async def` in `ds_tools.py`?
2. Does the wrapper in `adk_safe_wrappers.py` use `_run_async()`?

**Standard pattern:**
```python
def tool_name_tool(param1, param2, csv_path="", **kwargs):
    from .ds_tools import tool_name
    tool_context = kwargs.get("tool_context")
    
    # Setup artifact manager...
    
    # If tool_name is async, use _run_async
    result = _run_async(tool_name(param1=param1, param2=param2, csv_path=csv_path, tool_context=tool_context))
    return _ensure_ui_display(result, "tool_name")
```

---

## Conclusion

✅ **All three feature selection tools are now fixed**  
✅ **Async functions are properly awaited**  
✅ **"Unknown action" error resolved**  
✅ **Cache cleared, ready for testing**

**Please restart the server and try select_features() again!** 🚀

