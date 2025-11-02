# 🎯 ROOT CAUSE FIXED: Callback Wasn't Checking `__display__`

## The Problem You Reported

```
"describe shows null in the UI when I run display"
"only plot is working"
```

## What We Discovered

Looking at the UI trace:
```
result: null
status: "success"
```

And the session UI page:
```
Tool completed with status: **success**
```

**The tools ARE running successfully, but the UI isn't showing the data!**

## Root Cause Found

**File**: `data_science/callbacks.py`  
**Line 37** (before fix):

```python
# Extract text content
txt = result.get("ui_text") or result.get("message") or result.get("content") or result.get("summary")
```

**❌ THE BUG:** The callback extracts `ui_text`, `message`, `content`, or `summary` - but **NOT `__display__`**!

### Why plot() Worked

- plot() returns `ui_text` ✅ → Callback found it → UI showed it
- describe/head/stats return `__display__` ❌ → Callback missed it → UI showed `null`

### Why We Added `__display__` Everywhere

We added `__display__` to 175+ tools, added `_normalize_display()` to guarantee it exists, wrote ultra-aggressive LLM instructions... **but forgot the callback wasn't looking for it!**

---

## The Fix

**File**: `data_science/callbacks.py`

### Fix 1: UI Blocks (Line 37)
```python
# BEFORE
txt = result.get("ui_text") or result.get("message") or result.get("content") or result.get("summary")

# AFTER
txt = result.get("__display__") or result.get("ui_text") or result.get("message") or result.get("content") or result.get("summary") or result.get("text") or result.get("display")
```

### Fix 2: Chat Promotion (Line 207)
```python
# BEFORE
ui_text = result.get("ui_text") or result.get("message") or result.get("summary")

# AFTER
ui_text = result.get("__display__") or result.get("ui_text") or result.get("message") or result.get("summary") or result.get("text") or result.get("display") or result.get("content")
```

### Fix 3: Artifact Updates (Line 288)
```python
# BEFORE
existing = result.get("ui_text") or result.get("message") or ""
result["ui_text"] = (existing + ...).strip()

# AFTER
existing = result.get("__display__") or result.get("ui_text") or result.get("message") or ""
updated_text = (existing + ...).strip()
result["__display__"] = updated_text
result["ui_text"] = updated_text
result["message"] = updated_text
```

---

## Why This Was So Hard to Find

1. **Tools worked correctly** - No errors in logs
2. **safe_tool_wrapper worked** - Added `__display__` successfully
3. **_normalize_display worked** - Guaranteed field exists
4. **The callback was the only place that ignored it!**

The bug was in the OUTPUT layer, not the INPUT layer.

---

## What This Fixes

### Before (BROKEN):
```
describe() runs → Returns {__display__: "statistics...", status: "success"}
↓
Callback checks: ui_text? No. message? No. content? No.
↓
UI shows: result: null
```

### After (FIXED):
```
describe() runs → Returns {__display__: "statistics...", status: "success"}
↓
Callback checks: __display__? YES! ✅
↓
UI shows: Actual statistics table
```

---

## Server Restarted

✅ Stopped old server  
✅ Cleared all bytecode caches  
✅ Restarted with callback fix  
✅ No linter errors

---

## Test Now

### Expected Behavior:

**describe():**
```
✅ Dataset analyzed successfully!

**Shape:** 244 rows × 7 columns

**Columns:** total_bill, tip, sex, smoker, day, time, size

**Statistics:**
| Column | Mean | Std | Min | Max |
|--------|------|-----|-----|-----|
| total_bill | 19.79 | 8.90 | 3.07 | 50.81 |
...
```

**head():**
```
✅ First 5 rows:

| total_bill | tip | sex | smoker |
|-----------|-----|-----|--------|
| 16.99 | 1.01 | Female | No |
| 10.34 | 1.66 | Male | No |
...
```

**stats():**
```
✅ Statistical Analysis:

AI-powered insights:
- Dataset has 244 rows, 7 columns
- Missing values: 0
...
```

---

## Additional Fixes Applied

We also fixed:
1. **Streaming tools disabled** (line 3928 of agent.py) - Prevents auto-chaining
2. **Auto-run instructions removed** (line 3833 of agent.py) - No more "IMMEDIATELY: 1) analyze 2) describe"
3. **RULE #1 at top** (line 2520 of agent.py) - LLM sees critical display rule first

---

## Summary

| Component | Status |
|-----------|--------|
| Tools return `__display__` | ✅ Working (always did) |
| `_normalize_display()` | ✅ Working (always did) |
| `safe_tool_wrapper` | ✅ Working (always did) |
| **Callback checks `__display__`** | **✅ FIXED (was broken)** |
| UI displays results | **✅ SHOULD WORK NOW** |

---

## What to Test

1. **Upload tips.csv**
2. **Run describe()** - Should show statistics table
3. **Run head()** - Should show first rows
4. **Run stats()** - Should show AI insights
5. **Run plot()** - Should still work (as before)

**If you see actual data tables/stats instead of "result: null", the fix worked!** 🎉

---

## Why "Only plot() Working" Was the Key Clue

Your statement "only plot is working" was the breakthrough. It told us:

1. ✅ Server is running
2. ✅ Tools are executing
3. ✅ Tool wrappers are working
4. ❌ **Only the output display layer was broken**

plot() worked because it used `ui_text` (the old field name), while all other tools used `__display__` (the new, better field name).

The callback was stuck looking for the old field names!

---

**This should be the final fix. The callback was the missing link between working tools and visible output.**

## Server Status

🟢 **RESTARTED** with callback fix  
🟢 Ready to test

**Upload a file and try describe(), head(), or stats(). You should finally see data! 🚀**

