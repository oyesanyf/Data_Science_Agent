# Fixes #12 & #13 - Async/Await and Misleading Logs

## 🐛 **Bug #12: Async save_artifact Not Awaited**

### **Problem:**
```
RuntimeWarning: coroutine 'CallbackContext.save_artifact' was never awaited
  ctx.save_artifact(UI_FILENAME, part)  # line 139 in ui_page.py
```

### **Root Cause:**
The `publish_ui_blocks` function in `ui_page.py` was calling `ctx.save_artifact()` without `await`, causing a coroutine to never execute.

### **Fix Applied:**

#### **1. data_science/ui_page.py (Line 95)**
**Before:**
```python
def publish_ui_blocks(ctx: CallbackContext, tool_name: str, blocks: List[Dict[str, Any]]):
```

**After:**
```python
async def publish_ui_blocks(ctx: CallbackContext, tool_name: str, blocks: List[Dict[str, Any]]):
```

#### **2. data_science/ui_page.py (Line 139)**
**Before:**
```python
ctx.save_artifact(UI_FILENAME, part)  # fire-and-forget (ADK will surface in Artifacts)
```

**After:**
```python
await ctx.save_artifact(UI_FILENAME, part)  # Properly await the async call
```

#### **3. data_science/callbacks.py (Line 303)**
**Before:**
```python
publish_ui_blocks(callback_context, tool_name, blocks)
```

**After:**
```python
await publish_ui_blocks(callback_context, tool_name, blocks)
```

---

## 🐛 **Bug #13: Contradictory Log Messages**

### **Problem:**
```
05:17:21 - WARNING - No original filename found in upload. Will use default 'uploaded.csv'
05:17:21 - INFO - 📁 Original filename detected: uploaded.csv
```

This is **contradictory** - it says "No original filename found" but then claims "Original filename detected".

### **Root Cause:**
The code logged "detected" even when using the default fallback filename.

### **Fix Applied:**

#### **data_science/agent.py (Lines 1256-1266)**
**Before:**
```python
if not original_filename:
    logger.warning("No original filename found in upload. Will use default 'uploaded.csv'")
    original_filename = "uploaded.csv"

# 🔍 DEBUG: Log what we found
logger.info(f"📁 Original filename detected: {original_filename}")
print(f"📁 Original filename detected: {original_filename}")
```

**After:**
```python
if not original_filename:
    logger.warning("No original filename found in upload. Will use default 'uploaded.csv'")
    original_filename = "uploaded.csv"
    # Log that we're using default
    logger.info(f"📁 Using default filename: {original_filename}")
    print(f"📁 Using default filename: {original_filename}")
else:
    # Log that we detected actual filename
    logger.info(f"📁 Original filename detected: {original_filename}")
    print(f"📁 Original filename detected: {original_filename}")
```

---

## ✅ **Expected Behavior After Fixes**

### **Fix #12: Async Execution**
**Before:**
```
RuntimeWarning: coroutine 'CallbackContext.save_artifact' was never awaited
```

**After:**
```
[UI SINK] ✅ Artifact saved successfully: session_ui_page.md
```

### **Fix #13: Clear Logging**
**Before (Contradictory):**
```
WARNING - No original filename found in upload. Will use default 'uploaded.csv'
INFO - 📁 Original filename detected: uploaded.csv  # ❌ Misleading!
```

**After (Clear):**
```
WARNING - No original filename found in upload. Will use default 'uploaded.csv'
INFO - 📁 Using default filename: uploaded.csv  # ✅ Correct!
```

Or when filename IS found:
```
INFO - 📁 Original filename detected: my_data.csv  # ✅ Correct!
```

---

## 📊 **Summary of All Fixes (Now 13 Total)**

| Fix # | Issue | Files Changed | Status |
|-------|-------|---------------|--------|
| #1 | Memory Leak (7.93 GiB) | `ds_tools.py` | ✅ Fixed |
| #2 | Parquet Support | `ds_tools.py` | ✅ Fixed |
| #3 | Plot _exists() | `plot_tool_guard.py` | ✅ Fixed |
| #4-5 | MIME Detection | `artifact_manager.py`, `artifacts_io.py` | ✅ Fixed |
| #6 | Executive Report Async | `executive_report_guard.py` | ✅ Fixed |
| #7 | Debug Output | `head_describe_guard.py` | ✅ Fixed |
| #8-9 | Auto-bind Tools | `adk_safe_wrappers.py` | ✅ Fixed |
| #10 | Enhanced Logging | Multiple files | ✅ Fixed |
| #11 | State .keys() Bug | 5 files | ✅ Fixed |
| #12 | **Async save_artifact** | `ui_page.py`, `callbacks.py` | ✅ **FIXED** |
| #13 | **Misleading Logs** | `agent.py` | ✅ **FIXED** |

---

## 🚀 **Next Steps**

1. **Restart the server** to load fixes #12 and #13
2. **Upload a CSV** to verify:
   - No more RuntimeWarning about unawaited coroutines
   - Clear, non-contradictory log messages
3. **Verify UI artifacts** appear correctly

---

**All 13 fixes complete!** 🎉

