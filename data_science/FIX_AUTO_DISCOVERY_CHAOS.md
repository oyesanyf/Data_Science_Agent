# 🚨 CRITICAL BUG: Auto-Discovery Processing Multiple Files

## 🔍 Problem Found

When user uploads ONE file, the system is:
1. ❌ Discovering ALL old CSV files on disk
2. ❌ Processing each discovered file
3. ❌ Creating workspaces for each file
4. ❌ Calling old `dataset_workspace_manager` system (creates hash-based folders)

## 📍 Root Causes

### Cause #1: `rehydrate_session_state()` - Lines 764-782

**Location:** `artifact_manager.py`

```python
def rehydrate_session_state(state: Dict[str, Any]) -> None:
    # ...
    
    # If missing or not on disk, discover freshest on disk under UPLOAD_ROOT
    def _latest(patterns):
        from glob import glob
        candidates: list[str] = []
        # Search MULTIPLE locations including ALL subdirectories
        likely_roots = [
            _UPLOAD_ROOT,
            os.path.join(_UPLOAD_ROOT, ".uploaded"),
            os.path.join(_UPLOAD_ROOT, "uploads")
        ]
        for root in dict.fromkeys([p for p in likely_roots if p]):
            for pat in patterns:
                # ❌ RECURSIVE SEARCH finds ALL old files!
                candidates += glob(os.path.join(root, "**", pat), recursive=True)
        # ...
        return max(candidates, key=os.path.getmtime)  # ← Picks latest from ALL files
    
    if not csv_path or not os.path.exists(csv_path):
        candidate = _latest(["*.csv", "*.parquet"])  # ← Searches EVERYTHING!
        if candidate:
            state["default_csv_path"] = candidate  # ← Binds random old file!
```

**Problem:** Searches recursively through ALL workspace folders and binds random old files!

---

### Cause #2: `ensure_dataset_binding()` - Lines 316-332

**Location:** `agent.py`

```python
def ensure_dataset_binding(tool_context):
    # ...
    
    # Try workspace/uploads first
    ws_paths = state.get("workspace_paths", {})
    uploads_dir = ws_paths.get("uploads") or upload_root
    candidates = []
    
    for ext in ("*.csv",):
        # ❌ RECURSIVE search finds ALL old files!
        candidates += glob.glob(os.path.join(uploads_dir, "**", ext), recursive=True)
    
    if not candidates:
        # Try global upload_root fallback
        for ext in ("*.csv",):
            # ❌ ANOTHER recursive search!
            candidates += glob.glob(os.path.join(upload_root, "**", ext), recursive=True)
    
    # Pick the most recent file
    latest_file = max(candidates, key=os.path.getmtime)  # ← Random old file!
    state["default_csv_path"] = latest_file
```

**Problem:** Searches recursively and binds ANY old CSV it finds!

---

### Cause #3: `workspace_tools.py` Still Imports Old System

**Location:** `workspace_tools.py` lines 39, 108, 178, 247

```python
from .dataset_workspace_manager import (
    create_workspace_structure,  # ← OLD system with hash-based folders!
    ...
)
```

**Problem:** Old workspace manager creates folders like:
- `student_portuguese_clean_6af3b204` (hash suffix)
- `student_portuguese_clean_utf8_e117a84f` (hash suffix)

---

## 📊 Evidence from User's Directory

```
11/01/2025  05:20 PM    ads50                                    ← NEW system ✅
11/01/2025  05:22 PM    student_portuguese_clean_6af3b204        ← OLD system ❌
11/01/2025  05:23 PM    student_portuguese_clean_utf8_e117a84f   ← OLD system ❌
11/01/2025  05:23 PM    default                                  ← Fallback ❌
11/01/2025  05:23 PM    uploaded                                 ← Fallback ❌
11/01/2025  05:22 PM    _global                                  ← Fallback ❌
```

**Timestamps show:**
- 5:20 PM: First workspace created (ads50)
- 5:22 PM: Old system triggered (hash-based folders)
- 5:23 PM: Fallback logic triggered (default, uploaded)

**This means:** Within 3 minutes, THREE different workspace creation systems ran!

---

## 🎯 The Flow (What's Actually Happening)

```
User uploads: tips.csv
    ↓
1. NEW system (artifact_manager.ensure_workspace)
   → Creates: tips/20251101_172000/ ✅
    ↓
2. rehydrate_session_state() is called
   → Searches ALL directories recursively
   → Finds: old_file1.csv, old_file2.csv, old_file3.csv
   → Binds: old_file3.csv (most recent mtime)
    ↓
3. ensure_dataset_binding() is called
   → Searches AGAIN recursively
   → Finds MORE old files
   → Processes each one
    ↓
4. workspace_tools calls OLD dataset_workspace_manager
   → Creates: student_portuguese_clean_6af3b204/ ❌ (hash-based!)
    ↓
5. Fallback logic triggers
   → Creates: default/, _global/, uploaded/ ❌
    ↓
RESULT: 6 workspace folders for ONE upload! ❌❌❌
```

---

## ✅ Solution

### Fix #1: Disable Recursive Search in `rehydrate_session_state`

**Location:** `artifact_manager.py` line 776

```python
# BEFORE (BROKEN):
candidates += glob(os.path.join(root, "**", pat), recursive=True)  # ← Searches EVERYWHERE!

# AFTER (FIXED):
candidates += glob(os.path.join(root, pat), recursive=False)  # ← Only top level!
```

### Fix #2: Disable Recursive Search in `ensure_dataset_binding`

**Location:** `agent.py` lines 317, 322

```python
# BEFORE (BROKEN):
candidates += glob.glob(os.path.join(uploads_dir, "**", ext), recursive=True)

# AFTER (FIXED):
candidates += glob.glob(os.path.join(uploads_dir, ext), recursive=False)
```

### Fix #3: Only Bind CURRENT Upload, Not Old Files

**Add guard to rehydrate_session_state:**

```python
def rehydrate_session_state(state: Dict[str, Any]) -> None:
    # ...
    
    # ✅ NEW: Only search if NO file is already bound in this session
    if state.get("default_csv_path") and os.path.exists(state["default_csv_path"]):
        logger.info(f"[REHYDRATE] CSV already bound: {state['default_csv_path']}, skipping search")
        return  # ← Don't search for other files!
    
    # Only search if truly needed (no file in current session)
    if not csv_path or not os.path.exists(csv_path):
        # ... existing search logic
```

### Fix #4: Prevent workspace_tools from Calling Old System

**Option A:** Remove `workspace_tools` from agent registration  
**Option B:** Fix `workspace_tools.py` to use NEW `artifact_manager.ensure_workspace` instead

---

## 🔧 User's Suggestion: "Use session ID per dataset"

**Already implemented!** But being bypassed by auto-discovery.

Current logic:
```python
# Line 311-314: artifact_manager.py
run_id = callback_state.get("workspace_run_id")
if not run_id:
    run_id = time.strftime("%Y%m%d_%H%M%S")  # ← Session-based timestamp
    callback_state["workspace_run_id"] = run_id  # ← Persisted!
```

**This works perfectly!** The problem is that auto-discovery is:
1. Finding old files
2. Processing them
3. Each creates a NEW session with NEW run_id
4. Result: Multiple folders

---

## 📋 Implementation Plan

### Priority 1: Stop Processing Old Files (CRITICAL)

1. ✅ Modify `rehydrate_session_state`: Remove `recursive=True`
2. ✅ Modify `ensure_dataset_binding`: Remove `recursive=True`
3. ✅ Add guard: Only search if NO file bound in current session

### Priority 2: Fix workspace_tools

1. ✅ Remove `workspace_tools` from agent tool registration
2. OR: Modify `workspace_tools.py` to use `artifact_manager.ensure_workspace`

### Priority 3: Cleanup

1. ✅ Delete old hash-based folders
2. ✅ Delete fallback folders (default, _global)

---

## 🎯 Expected Result After Fix

```
User uploads: tips.csv (ONE file)
    ↓
1. NEW system creates: tips/20251101_172000/ ✅
    ↓
2. rehydrate_session_state checks: File already bound? YES
   → Skips search ✅
    ↓
3. ensure_dataset_binding checks: File already bound? YES
   → Skips search ✅
    ↓
RESULT: ONE workspace folder for ONE upload! ✅✅✅
```

---

**Status:** ⚠️ CRITICAL BUG FOUND  
**Impact:** Creates 3-6 workspace folders per upload  
**Confidence:** 95% (Root cause identified with evidence)  
**Next Step:** Apply fixes to `artifact_manager.py` and `agent.py`

