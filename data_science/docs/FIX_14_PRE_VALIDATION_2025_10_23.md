# Fix #14: Pre-Validation for head/describe/shape Tools

## 🎯 **User's Critical Insight**

> "if head describe of size can not run against the correct dataset the code will fail"

**ABSOLUTELY RIGHT!** Without proper validation, the tools would fail silently or return empty results when `csv_path` was missing.

---

## 🐛 **The Problem**

**Before this fix:**
1. LLM calls `head()` or `describe()` or `shape()` without `csv_path`
2. Tools attempt auto-binding from state
3. **IF auto-binding fails, tools proceed with empty `csv_path`**
4. Inner functions fail or return empty results
5. User sees "dataset appears empty" even though dataset is valid!

---

## ✅ **The Solution: Pre-Validation**

Added **validation BEFORE tool execution** to prevent failures:

### **Files Modified:**

#### **1. data_science/head_describe_guard.py**

**For `head_tool_guard` (Lines 26-57):**
```python
# 🛡️ PRE-VALIDATION: Check if csv_path is available (from kwargs or state)
csv_path = kwargs.get('csv_path', '')
if not csv_path and tool_context and hasattr(tool_context, 'state'):
    csv_path = (tool_context.state.get("default_csv_path") or 
               tool_context.state.get("dataset_csv_path") or "")
    if csv_path:
        print(f"[HEAD GUARD] ✅ Auto-recovered csv_path from state: {csv_path}", flush=True)

if not csv_path:
    # Return helpful error IMMEDIATELY - don't proceed with empty path
    return {
        "status": "error",
        "message": (
            "❌ **Cannot run head() - No dataset specified!**\n\n"
            "**Quick Fix:**\n"
            "1. Upload a CSV file first\n"
            "2. Run `list_data_files()` to see available files\n"
            "3. Run `analyze_dataset(csv_path='your_file.csv')` to set default\n"
            "4. Or pass `csv_path` explicitly\n"
        ),
        "error": "missing_csv_path"
    }

# Only proceed if validation passed
print(f"[HEAD GUARD] ✅ Validation passed - csv_path: {csv_path}", flush=True)
result = _head_inner(tool_context=tool_context, **kwargs)
```

**For `describe_tool_guard` (Lines 158-189):**
```python
# Same validation logic as head_tool_guard
# Ensures describe() never runs without a valid dataset
```

#### **2. data_science/adk_safe_wrappers.py**

**For `shape_tool` (Lines 768-790):**
```python
# 🛡️ PRE-VALIDATION: Ensure csv_path is available before proceeding
if not csv_path:
    logger.error("[shape_tool] Validation failed: No csv_path available")
    return {
        "status": "error",
        "message": (
            "❌ **Cannot get shape - No dataset specified!**\n\n"
            "**Quick Fix:**\n"
            "1. Upload a CSV file first\n"
            "2. Run `analyze_dataset(csv_path='your_file.csv')` to set default\n"
            "3. Or pass `csv_path` explicitly: `shape(csv_path='your_file.csv')`\n"
        ),
        "error": "missing_csv_path",
        "rows": 0,
        "columns": 0
    }

logger.info(f"[shape_tool] Validation passed - proceeding with csv_path: {csv_path}")
return shape(csv_path=csv_path, tool_context=tool_context)
```

---

## 📊 **Validation Flow**

```
LLM calls head/describe/shape()
        ↓
[1] Check kwargs for csv_path
        ↓
[2] If not found, try auto-bind from state
        ↓
[3] PRE-VALIDATION: Is csv_path available?
        ↓
    YES → Proceed with tool execution ✅
        ↓
    NO → Return helpful error immediately ❌
        (Don't execute inner tool!)
```

---

## 🎯 **Benefits**

1. **Fail Fast**: Errors caught BEFORE tool execution
2. **Clear Messages**: Users get actionable instructions
3. **No Silent Failures**: Tools never proceed with invalid state
4. **LLM Visibility**: Error messages are properly formatted for LLM consumption
5. **State Recovery**: Auto-binding from state still works as fallback

---

## 🚀 **Expected Console Output (After Upload)**

### **Case 1: Valid Dataset (Success)**
```
================================================================================
[HEAD GUARD] STARTING
================================================================================
[HEAD GUARD] kwargs keys: ['tool_context']
[HEAD GUARD] csv_path: NOT PROVIDED
[HEAD GUARD] ✅ Auto-recovered csv_path from state: 1761215442_uploaded.csv
[HEAD GUARD] ✅ Validation passed - csv_path: 1761215442_uploaded.csv
[HEAD GUARD] head_tool returned: <class 'dict'>, keys=['status', 'head', 'shape']
```

### **Case 2: Missing Dataset (Validation Failure)**
```
================================================================================
[HEAD GUARD] STARTING
================================================================================
[HEAD GUARD] kwargs keys: ['tool_context']
[HEAD GUARD] csv_path: NOT PROVIDED
[HEAD GUARD] ❌ VALIDATION FAILED - No csv_path available
[HEAD GUARD] Returning error message to LLM
```

**LLM sees:**
```
❌ **Cannot run head() - No dataset specified!**

**Quick Fix:**
1. Upload a CSV file first
2. Run `list_data_files()` to see available files
3. Run `analyze_dataset(csv_path='your_file.csv')` to set default
```

---

## 📋 **All 14 Fixes Now Active**

1. ✅ Memory Leak Fix
2. ✅ Parquet Support
3. ✅ Plot Generation
4. ✅ MIME Types (Artifacts)
5. ✅ MIME Types (I/O)
6. ✅ Executive Reports Async
7. ✅ Debug Print Statements
8. ✅ Auto-bind describe_tool
9. ✅ Auto-bind shape_tool
10. ✅ analyze_dataset csv_path passing
11. ✅ State .keys() fixes (5 files)
12. ✅ Async save_artifact
13. ✅ Filename logging clarity
14. ✅ **Pre-Validation (head/describe/shape)** ← NEW!

---

## 🔍 **Why This Fix Was Critical**

Without pre-validation:
- Tools would run with `csv_path=""` or `None`
- Inner functions would fail or return `{}`
- LLM would see "dataset appears empty"
- Users would be confused (they uploaded a file!)

With pre-validation:
- Tools validate BEFORE execution
- Clear error messages guide users
- Auto-recovery from state still works
- No silent failures or empty results!

---

## ✅ **Server Status**

- Cache cleared (force refresh)
- All 14 fixes loaded
- Ready for testing with CSV upload!

