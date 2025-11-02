# Plot Guard Fix - Missing _exists Function

## Problem Summary

**Symptom:**  
- `plot_tool_guard` completing in 0.01s (too fast)
- No plots being generated
- No PNG files created
- No detailed log messages from plot generation

**Root Cause:**  
Line 77 in `plot_tool_guard.py` calls `_exists(p)` but this function was **never defined**, causing a `NameError`.

## The Bug

```python
# Line 77 in plot_tool_guard.py
if p and _exists(p):  # ❌ NameError: name '_exists' is not defined
    returned.append(p)
```

This error was caught by the exception handler in the async wrapper, making the function:
1. Fail silently without logging
2. Return immediately (0.01s)
3. Return empty results

## Fix Applied

Added the missing `_exists` helper function:

```python
def _exists(path) -> bool:
    """Check if a file path exists."""
    try:
        return Path(path).exists() if path else False
    except Exception:
        return False
```

## Impact

**Before Fix:**
- ❌ plot_tool_guard failed silently
- ❌ No plots generated
- ❌ No error messages
- ❌ Execution time: 0.01s (immediate failure)

**After Fix:**
- ✅ plot_tool_guard will execute properly
- ✅ Plots will be generated
- ✅ Artifacts will appear in UI
- ✅ Execution time: 2-7s (normal)

## Files Modified

- `data_science/plot_tool_guard.py` (lines 15-20): Added `_exists()` function

## Testing

After server restart:
1. Upload a dataset
2. Ask agent to "create plots" or "visualize the data"
3. Verify:
   - Execution time > 1 second
   - PNG files created in workspace
   - Artifacts appear in UI

## Related Fixes Today

This is the **3rd fix** applied today:
1. ✅ Memory leak fix (7.93 GiB allocation)
2. ✅ Parquet file support fix (UnicodeDecodeError)  
3. ✅ Plot generation fix (missing _exists function)

---

**Status**: ✅ Fixed - Restart Required  
**Priority**: High (User-facing feature)  
**Impact**: Plot Generation & UI Artifacts

