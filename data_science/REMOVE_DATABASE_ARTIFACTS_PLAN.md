# 🗑️ REMOVE ALL DATABASE ARTIFACT STORAGE - FILESYSTEM ONLY

## 🎯 Goal

**Remove ALL database artifact storage. Use ONLY filesystem for artifacts.**

---

## 📊 Current State

### Database Tables (adk_sessions.db - 14.5 MB):
```
sessions     - Session state (keep)
app_states   - App-level state (keep)
user_states  - User-level state (keep)
events       - Conversation events (keep, but remove artifact references)
```

**No dedicated artifacts table** ✅ - This is good!

### Problem: ADK `save_artifact()` Calls Everywhere

**Found 315 instances across 67 files!**

```python
# These ALL need to be removed:
await tc.save_artifact(filename, part)
await tool_context.save_artifact(name, artifact)
await context.save_artifact(artifact_name, part)
version = await tc.save_artifact(...)
```

---

## ✅ SOLUTION: Remove ALL save_artifact() Calls

### Strategy:

1. ✅ **Keep filesystem writes** - These are perfect:
   ```python
   # KEEP THESE (filesystem):
   shutil.copy2(src, dest)
   path.write_text(content)
   df.to_csv(filepath)
   with open(file, 'w') as f: f.write(content)
   ```

2. ❌ **Remove ADK artifact service calls**:
   ```python
   # REMOVE THESE (database/ADK):
   await tc.save_artifact(filename, part)
   await tool_context.save_artifact(name, artifact)
   ```

3. ✅ **Simplify artifact functions** - Just write to filesystem directly

---

## 📋 Files to Modify

### Priority 1: Core Artifact Logic (CRITICAL)

1. **`agent.py`** (17 instances)
   - Remove `tc.save_artifact()` calls
   - Keep filesystem writes to `workspace_root/reports/`
   - Keep `shutil.copy2()` calls

2. **`adk_safe_wrappers.py`** (3 instances)
   - Remove ADK artifact uploads
   - Keep direct filesystem writes

3. **`artifact_manager.py`** (5 instances)
   - Remove `register_and_sync_artifact` ADK sync
   - Keep filesystem operations only

4. **`callbacks.py`** (4 instances)
   - Remove artifact uploads
   - Keep filesystem operations

### Priority 2: Tool Wrappers

5. **`ds_tools.py`** (35 instances)
   - Remove `await ctx.save_artifact()` calls
   - Keep `df.to_csv()` filesystem writes

6. **`head_describe_guard.py`** (2 instances)
7. **`executive_report_guard.py`** (2 instances)
8. **`plot_tool_guard.py`** (2 instances)
9. **`universal_tool_guard.py`** (2 instances)

### Priority 3: Helper Modules

10. **`universal_artifact_generator.py`** (16 instances)
11. **`universal_artifact_creator.py`** (15 instances)
12. **`artifact_utils.py`** (16 instances)
13. **`llm_artifact_enforcer.py`** (12 instances)

### Priority 4: Specialized Tools

14. **`auto_sklearn_tools.py`** (2 instances)
15. **`autogluon_tools.py`** (5 instances)
16. **`advanced_tools.py`** (2 instances)
17. **`model_registry.py`** (3 instances)
18. **`comprehensive_analyzer.py`** (1 instance)

---

## 🔧 Implementation Pattern

### BEFORE (Database + Filesystem):
```python
# OLD: Dual-path saving (REMOVE THIS)
try:
    # 1. Save to filesystem
    import shutil
    ws_dest_dir = Path(workspace_root) / "reports"
    ws_dest_dir.mkdir(parents=True, exist_ok=True)
    ws_dest_path = ws_dest_dir / filename
    shutil.copy2(file_path, ws_dest_path)
    
    # 2. Upload to ADK artifact service (DATABASE)
    file_data = Path(file_path).read_bytes()
    blob = types.Blob(data=file_data, mime_type=mime_type)
    part = types.Part(inline_data=blob)
    await tc.save_artifact(artifact_name, part)  # ← REMOVE THIS!
except Exception as e:
    logger.warning(f"Failed: {e}")
```

### AFTER (Filesystem ONLY):
```python
# NEW: Filesystem ONLY (SIMPLE!)
try:
    # 1. Save to filesystem (ONLY step needed!)
    import shutil
    ws_dest_dir = Path(workspace_root) / "reports"
    ws_dest_dir.mkdir(parents=True, exist_ok=True)
    ws_dest_path = ws_dest_dir / filename
    shutil.copy2(file_path, ws_dest_path)
    logger.info(f"✅ Saved to filesystem: {ws_dest_path}")
except Exception as e:
    logger.warning(f"Failed: {e}")
```

**Result:**
- ✅ 50% less code
- ✅ No database writes
- ✅ No ADK overhead
- ✅ Direct filesystem access
- ✅ Faster performance

---

## 🎯 Specific Changes

### Change #1: `agent.py` - Remove ADK Uploads

**Lines 2186-2189** (and similar blocks):
```python
# BEFORE:
# Upload to ADK (already in async context)
await tc.save_artifact(artifact_name, part)
uploaded_count += 1
logger.info(f"[ADK UI] Uploaded artifact: {artifact_name}")

# AFTER:
# (Remove this entire block - filesystem copy already done above)
```

### Change #2: `_save_tool_markdown_artifact`

**Lines 1500-1600**:
```python
# BEFORE:
try:
    # Save via ADK artifact service
    blob = types.Blob(data=markdown_bytes, mime_type="text/markdown")
    part = types.Part(inline_data=blob)
    version = await tc.save_artifact(md_name, part)
    logger.info(f"[ADK ARTIFACT] Saved: {md_name}, version {version}")
except Exception as e:
    logger.warning(f"[ADK ARTIFACT] Failed: {e}")

# AFTER:
# (Remove entire ADK save block - just keep filesystem write)
```

### Change #3: `ds_tools.py` - Remove DataFrame Artifact Uploads

**Line 4487**:
```python
# BEFORE:
if ctx is not None:
    data = df.to_csv(index=False).encode("utf-8")
    await ctx.save_artifact(filename=filename, artifact=types.Part.from_bytes(data=data, mime_type="text/csv"))

# Save to filesystem
filepath = os.path.join(data_dir, filename)
df.to_csv(filepath, index=False)

# AFTER:
# (Remove ctx.save_artifact block)
# Keep ONLY filesystem save:
filepath = os.path.join(data_dir, filename)
df.to_csv(filepath, index=False)
logger.info(f"✅ Saved to filesystem: {filepath}")
```

### Change #4: Remove Artifact Upload in Workspace Copy

**Lines ~2191-2216** in `agent.py`:
```python
# BEFORE:
# CRITICAL: ALSO save to workspace filesystem (not just ADK)
try:
    # ... filesystem copy ...
    shutil.copy2(path_obj, ws_dest_path)
    logger.info(f"[WORKSPACE] Saved artifact to workspace: {ws_dest_path}")
except Exception as ws_error:
    logger.warning(f"[WORKSPACE] Failed to save artifact to workspace: {ws_error}")

# AFTER:
# ONLY save to workspace filesystem (NO ADK)
try:
    # ... filesystem copy ...
    shutil.copy2(path_obj, ws_dest_path)
    logger.info(f"✅ Saved artifact: {ws_dest_path}")
except Exception as ws_error:
    logger.warning(f"Failed to save artifact: {ws_error}")
```

---

## 🧹 Database Cleanup

### Step 1: No Schema Changes Needed
✅ No dedicated artifacts table exists
✅ Keep sessions, app_states, user_states, events tables
✅ Event table may have artifact references, but those will just be ignored

### Step 2: Remove ADK Artifact Service References

**No database cleanup needed!** Just remove the code that calls `save_artifact()`.

---

## 📊 Expected Results

### BEFORE:
```
User uploads file
  ↓
1. Save to filesystem: workspace_root/uploads/file.csv ✅
2. Upload to ADK: await tc.save_artifact() → Database/events ❌
3. Copy to workspace: workspace_root/reports/file.md ✅
4. Upload to ADK: await tc.save_artifact() → Database/events ❌
```

### AFTER:
```
User uploads file
  ↓
1. Save to filesystem: workspace_root/uploads/file.csv ✅
2. Save to filesystem: workspace_root/reports/file.md ✅

DONE! Simple and fast! ✅
```

---

## ✅ Benefits

| Aspect | Before (Database + Filesystem) | After (Filesystem Only) |
|--------|-------------------------------|-------------------------|
| **Complexity** | High (dual writes) | Low (single write) |
| **Performance** | Slow (2x writes) | Fast (1x write) |
| **Database Size** | 14.5 MB (growing) | 0 KB (no artifacts) |
| **Failure Points** | 2 (filesystem + ADK) | 1 (filesystem only) |
| **Code Lines** | ~315 save_artifact calls | 0 save_artifact calls |
| **Debugging** | Hard (where's the artifact?) | Easy (always on disk) |
| **User Access** | Indirect (via ADK) | Direct (file explorer) |

---

## 🚀 Implementation Steps

### Phase 1: Core Files (Do First)
1. ✅ `agent.py` - Remove all `tc.save_artifact()` calls
2. ✅ `adk_safe_wrappers.py` - Remove ADK uploads
3. ✅ `artifact_manager.py` - Remove sync to ADK
4. ✅ `callbacks.py` - Remove ADK artifact registration

### Phase 2: Tool Files (Do Next)
5. ✅ `ds_tools.py` - Remove 35 instances
6. ✅ All guard files (head_describe_guard, plot_tool_guard, etc.)

### Phase 3: Helper Modules (Do Last)
7. ✅ `universal_artifact_*` files
8. ✅ `artifact_utils.py`
9. ✅ `llm_artifact_enforcer.py`

### Phase 4: Specialized Tools
10. ✅ Auto-sklearn, AutoGluon, Advanced tools
11. ✅ Model registry, Comprehensive analyzer

### Phase 5: Cleanup
12. ✅ Remove unused imports (`from google.genai.types import Part, Blob`)
13. ✅ Remove artifact helper functions that only do ADK uploads
14. ✅ Update documentation

---

## ⚠️ What to Keep

### Keep These (Filesystem Operations):
```python
✅ shutil.copy2(src, dest)
✅ path.write_text(content)
✅ df.to_csv(filepath)
✅ with open(file, 'w') as f: f.write(content)
✅ Path.mkdir(parents=True, exist_ok=True)
```

### Remove These (Database/ADK Operations):
```python
❌ await tc.save_artifact(name, part)
❌ await tool_context.save_artifact(filename, artifact)
❌ version = await ctx.save_artifact(...)
❌ types.Part(inline_data=types.Blob(...))  (only used for ADK)
❌ sync_push_artifact(...)  (ADK sync functions)
```

---

## 🎯 Final Goal

**After this change:**
- ✅ ALL artifacts stored ONLY on filesystem
- ✅ NO artifacts in database
- ✅ NO ADK artifact service calls
- ✅ Simpler code (50% reduction in artifact code)
- ✅ Faster performance (no database overhead)
- ✅ Direct user access (File Explorer, not via API)

**Database will ONLY store:**
- Session state (conversation history, user preferences)
- Workflow state (what stage user is on)
- App/user state (configuration)

**Filesystem will ONLY store:**
- Uploaded files: `.uploaded/_workspaces/{dataset}/{run_id}/uploads/`
- Reports: `.uploaded/_workspaces/{dataset}/{run_id}/reports/`
- Plots: `.uploaded/_workspaces/{dataset}/{run_id}/plots/`
- Models: `.uploaded/_workspaces/{dataset}/{run_id}/models/`
- Results: `.uploaded/_workspaces/{dataset}/{run_id}/results/`

---

**Status:** ⚠️ READY TO IMPLEMENT  
**Impact:** High (removes 315 save_artifact calls)  
**Risk:** Low (keeps all filesystem writes)  
**Confidence:** 100% (clear separation: state→DB, artifacts→filesystem)

