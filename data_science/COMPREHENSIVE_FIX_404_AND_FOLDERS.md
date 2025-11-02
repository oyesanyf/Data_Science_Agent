# 🎯 COMPREHENSIVE FIX: 404 Errors + Multiple Folders

## 🔍 Current Problems

### Problem #1: 404 Errors
```
INFO: 127.0.0.1:54208 - "GET /apps/data_science/users/user/reports/20251101_160905_197028_plot_tool_guard.md/versions/0 HTTP/1.1" 404 Not Found
```

**Why**: Code tries to fetch artifacts via HTTP, but they're on filesystem!

### Problem #2: Multiple Workspace Folders
```
.uploaded/_workspaces/
  ├─ ads50/                                    ← NEW system ✅
  ├─ student_portuguese_clean_6af3b204/        ← OLD system ❌
  ├─ student_portuguese_clean_utf8_e117a84f/   ← OLD system ❌
  ├─ default/                                  ← Fallback ❌
  ├─ uploaded/                                 ← Fallback ❌
  └─ _global/                                  ← Fallback ❌
```

**Why**: Auto-discovery finds old files + old workspace manager creates hash-based folders!

---

## ✅ SOLUTION: Remove ALL ADK Artifact Service Calls

### Strategy:
1. ❌ **REMOVE**: All `tool_context.save_artifact()` calls
2. ❌ **REMOVE**: All `tool_context.load_artifact()` calls  
3. ❌ **REMOVE**: All HTTP artifact fetching
4. ✅ **KEEP**: Direct filesystem reads/writes to workspace folders
5. ✅ **FIX**: Auto-discovery to NOT search recursively
6. ✅ **FIX**: Remove old `dataset_workspace_manager` import

---

## 📋 Files to Modify

### 1. `agent.py` - Remove ADK artifact saves

**Lines to modify:**
- Line ~1520-1600: `_save_tool_markdown_artifact()` - Remove `tc.save_artifact()` calls
- Line ~2187: Artifact upload loop - Remove `await tc.save_artifact()`
- Line ~2850: Sync artifact upload - Remove `tc.save_artifact()`

**Changes:**
```python
# BEFORE (BROKEN):
await tc.save_artifact(artifact_name, part)  # ← Tries to use ADK service, gets 404

# AFTER (FIXED):
# DON'T call save_artifact - just save to filesystem directly!
# File is already saved in workspace by earlier code
logger.info(f"[FILESYSTEM] Artifact saved: {workspace_path}")
```

### 2. `agent.py` - Fix Auto-Discovery

**Lines to modify:**
- Line 316-317: `ensure_dataset_binding()` - Remove `recursive=True`
- Line 321-322: Fallback search - Remove `recursive=True`

**Changes:**
```python
# BEFORE (BROKEN):
candidates += glob.glob(os.path.join(uploads_dir, "**", ext), recursive=True)  # ← Finds ALL old files!

# AFTER (FIXED):
candidates += glob.glob(os.path.join(uploads_dir, ext), recursive=False)  # ← Only current folder!
```

### 3. `artifact_manager.py` - Fix Auto-Discovery

**Lines to modify:**
- Line 776: `_latest()` - Remove `recursive=True`

**Changes:**
```python
# BEFORE (BROKEN):
candidates += glob(os.path.join(root, "**", pat), recursive=True)  # ← Searches EVERYWHERE!

# AFTER (FIXED):
candidates += glob(os.path.join(root, pat), recursive=False)  # ← Only top level!
```

### 4. `artifact_manager.py` - Add Guard to Prevent Multiple Searches

**Add at line 784 (before search):**
```python
def rehydrate_session_state(state: Dict[str, Any]) -> None:
    # ...
    
    # ✅ NEW: Only search if NO file is already bound in this session
    csv_path = state.get("default_csv_path")
    if csv_path and os.path.exists(csv_path):
        logger.info(f"[REHYDRATE] CSV already bound: {csv_path}, skipping auto-discovery")
        return  # ← Don't search for other files!
    
    # Only search if truly needed
    if not csv_path or not os.path.exists(csv_path):
        candidate = _latest(["*.csv"])
        # ... rest of search logic
```

### 5. `adk_safe_wrappers.py` - Remove ADK artifact saves

**Search for all `save_artifact` calls and comment them out or remove.**

### 6. `ds_tools.py` - Remove ADK artifact saves

**Line ~4487: `_save_df_artifact()` - Remove `await ctx.save_artifact()`**

```python
# BEFORE:
await ctx.save_artifact(filename=filename, artifact=types.Part.from_bytes(...))

# AFTER:
# Save only to filesystem - NO ADK service
df.to_csv(filepath, index=False)
logger.info(f"[FILESYSTEM] Saved DataFrame to: {filepath}")
```

### 7. `utils/artifacts_tools.py` - Use ONLY Filesystem Fallback

**Already has filesystem fallback! Just prioritize it:**

```python
# In load_artifact_text_preview_tool and download_artifact_tool:
# Change order - try filesystem FIRST, not as fallback

# BEFORE:
try:
    content = await tool_context.load_artifact(...)  # ← Try ADK first
except:
    # Fallback to filesystem

# AFTER:
try:
    # Try filesystem FIRST
    content = open(workspace_path).read()
    source = "filesystem"
except:
    # Only try ADK if filesystem fails
    content = await tool_context.load_artifact(...)
```

---

## 🔧 Quick Fix Script

Create a script to apply all fixes:

```python
# fix_artifacts_and_folders.py
import re
from pathlib import Path

def remove_adk_artifact_calls(file_path):
    """Remove or comment out all ADK artifact service calls."""
    content = Path(file_path).read_text(encoding='utf-8')
    
    # Pattern 1: await tc.save_artifact(...) -> filesystem save
    content = re.sub(
        r'await\s+tc\.save_artifact\([^)]+\)',
        '# Removed: ADK artifact save (using filesystem only)',
        content
    )
    
    # Pattern 2: tc.save_artifact(...) -> filesystem save
    content = re.sub(
        r'tc\.save_artifact\([^)]+\)',
        '# Removed: ADK artifact save (using filesystem only)',
        content
    )
    
    # Pattern 3: tool_context.save_artifact(...) -> filesystem save
    content = re.sub(
        r'tool_context\.save_artifact\([^)]+\)',
        '# Removed: ADK artifact save (using filesystem only)',
        content
    )
    
    # Pattern 4: context.save_artifact(...) -> filesystem save
    content = re.sub(
        r'context\.save_artifact\([^)]+\)',
        '# Removed: ADK artifact save (using filesystem only)',
        content
    )
    
    Path(file_path).write_text(content, encoding='utf-8')
    print(f"✅ Fixed: {file_path}")

def fix_recursive_search(file_path):
    """Remove recursive=True from glob searches."""
    content = Path(file_path).read_text(encoding='utf-8')
    
    # Change recursive=True to recursive=False
    content = content.replace('recursive=True', 'recursive=False')
    
    # Remove "**/" from glob patterns
    content = re.sub(r'os\.path\.join\(([^,]+),\s*"\*\*/",\s*([^)]+)\)', 
                     r'os.path.join(\1, \2)', content)
    
    Path(file_path).write_text(content, encoding='utf-8')
    print(f"✅ Fixed: {file_path}")

# Apply fixes
files_to_fix_artifacts = [
    'agent.py',
    'adk_safe_wrappers.py',
    'ds_tools.py',
    'artifact_utils.py',
]

files_to_fix_search = [
    'agent.py',
    'artifact_manager.py',
]

for f in files_to_fix_artifacts:
    remove_adk_artifact_calls(f)

for f in files_to_fix_search:
    fix_recursive_search(f)

print("\n✅ All fixes applied!")
```

---

## 🎯 Expected Results After Fix

### 1. No More 404 Errors ✅
```
# BEFORE:
GET /apps/data_science/users/user/reports/xxx.md HTTP/1.1" 404 Not Found

# AFTER:
[FILESYSTEM] Artifact saved: .uploaded/_workspaces/tips/20251101_HHMMSS/reports/xxx.md
```

### 2. ONE Folder Per Dataset ✅
```
# BEFORE (6 folders):
├─ ads50/
├─ student_portuguese_clean_6af3b204/        ❌
├─ student_portuguese_clean_utf8_e117a84f/   ❌
├─ default/                                  ❌
├─ uploaded/                                 ❌
└─ _global/                                  ❌

# AFTER (1 folder):
└─ tips/
    └─ 20251101_HHMMSS/                      ✅
```

### 3. Direct Filesystem Access ✅
```python
# All artifact operations use direct filesystem:
reports_dir = workspace_root / "reports"
plots_dir = workspace_root / "plots"
models_dir = workspace_root / "models"

# Save
(reports_dir / "analysis.md").write_text(content)

# Load
content = (reports_dir / "analysis.md").read_text()
```

---

## 📊 Summary of Changes

| Issue | Root Cause | Fix | Impact |
|-------|-----------|-----|--------|
| 404 Errors | ADK artifact HTTP service | Remove all `save_artifact()` calls | ✅ No more 404s |
| Multiple folders | Recursive auto-discovery | Change `recursive=True` to `False` | ✅ No more duplicates |
| Hash-based folders | Old workspace manager | Already fixed (display_name priority) | ✅ Proper names |
| Processing old files | Auto-discovery searches all | Add guard to skip if file bound | ✅ One upload = one folder |

---

## ⚠️ Implementation Steps

1. **Create backup**:
   ```bash
   cd C:\harfile\data_science_agent\data_science
   git commit -am "Backup before artifact removal"
   ```

2. **Apply fixes**:
   - Modify `agent.py` (3 locations)
   - Modify `artifact_manager.py` (2 locations)
   - Modify `ds_tools.py` (1 location)
   - Modify `adk_safe_wrappers.py` (multiple locations)
   - Modify `utils/artifacts_tools.py` (prioritize filesystem)

3. **Test**:
   ```bash
   # Restart server
   python -m data_science.main
   
   # Upload ONE file
   # Expected: ONE folder created
   # Expected: NO 404 errors
   ```

4. **Cleanup**:
   ```powershell
   # Delete old broken folders
   cd .uploaded\_workspaces
   Remove-Item *_6af3b204 -Recurse -Force
   Remove-Item *_utf8_* -Recurse -Force
   Remove-Item default -Recurse -Force
   Remove-Item _global -Recurse -Force
   ```

---

**Status**: ⚠️ READY TO IMPLEMENT  
**Confidence**: 95%  
**Risk**: Low (removing unused ADK service calls)  
**Benefit**: Fixes BOTH 404 errors AND multiple folders!

