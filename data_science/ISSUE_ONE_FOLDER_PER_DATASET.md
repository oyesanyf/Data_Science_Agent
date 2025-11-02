# ⚠️ ISSUE: One Folder Per Dataset - Partially Working

## 📊 Current Status

### ✅ WORKS When Dataset Name Detected

```
.uploaded/_workspaces/
  ├─ ads50/
  │   └─ 20251101_151122/  ✅ Single run folder
  │       ├─ uploads/
  │       ├─ reports/
  │       ├─ plots/
  │       └─ models/
  │
  └─ student_portuguese_clean/
      └─ 20251101_160123/  ✅ Single run folder
          ├─ uploads/
          ├─ reports/
          ├─ plots/
          └─ models/
```

**Result:** ✅ Each dataset has ONE folder, with timestamped runs inside.

---

### ❌ FAILS When Dataset Name Not Detected

```
.uploaded/_workspaces/
  └─ uploaded/  ← Fallback name used
      ├─ 20251101_151210/  ❌
      ├─ 20251101_151233/  ❌
      ├─ 20251101_151236/  ❌
      ├─ 20251101_160304/  ❌
      ├─ 20251101_160321/  ❌
      ├─ 20251101_160754/  ❌
      ├─ 20251101_160905/  ❌
      ├─ 20251101_161027/  ❌
      ├─ 20251101_161134/  ❌
      ├─ 20251101_161242/  ❌
      ├─ 20251101_161335/  ❌
      └─ 20251101_161646/  ❌  (16 folders!)
```

**Result:** ❌ Each upload creates a NEW `uploaded/{timestamp}/` folder when dataset name extraction fails.

---

## 🔍 Root Cause

### The Logic Chain:

1. **User uploads file:** `tips.csv`
2. **System saves as:** `1762000000_uploaded.csv` (timestamp prefix)
3. **Dataset name extraction attempts:**
   - ✅ Try `display_name` (blob metadata) → May contain "tips.csv"
   - ✅ Try `original_filename` → May contain "tips.csv"
   - ✅ Try filepath basename → Contains "1762000000_uploaded.csv"
   - ✅ Try CSV headers → May contain generic column names
4. **If all fail:** Falls back to `"uploaded"`
5. **Workspace created:** `uploaded/20251101_HHMMSS/`

### Why It Fails:

**Scenario 1: display_name is empty/missing**
```python
display_name_for_slug = part.inline_data.display_name  # ← May be None or empty
```

**Scenario 2: Filename is generic**
```python
filepath = "1762000000_uploaded.csv"  # ← After timestamp prefix added
base = Path(filepath).stem  # ← "1762000000_uploaded"
base = re.sub(r"^\d{10,}_", "", base)  # ← "uploaded" ❌
```

**Scenario 3: Headers are generic**
```python
headers = ['Unnamed: 0', 'column1', 'column2']  # ← Too generic
# LLM can't derive meaningful name
```

---

## 📋 The Code Path

### Location: `agent.py` lines 4415-4445

```python
# Get display_name from blob (if available)
display_name_for_slug = None
try:
    if hasattr(part, 'inline_data') and hasattr(part.inline_data, 'display_name'):
        display_name_for_slug = part.inline_data.display_name
        logger.info(f"[DATASET NAME] Found display_name: {display_name_for_slug}")
except Exception:
    pass

# Try to derive from CSV headers
slug = derive_dataset_slug(
    state,
    headers=headers,
    filepath=filepath_str,  # ← Already has timestamp prefix!
    sample_summary=sample_summary,
    display_name=display_name_for_slug or original_filename  # ← Fallback chain
)
```

---

## 🐛 Issues Found

### Issue #1: `display_name` Not Always Available
**Location:** Browser upload blob metadata  
**Problem:** ADK may not populate `part.inline_data.display_name` consistently

### Issue #2: Filename Already Transformed
**Location:** `large_data_handler.save_upload()`  
**Problem:** By the time `derive_dataset_slug()` is called, filename is already `{timestamp}_uploaded.csv`

### Issue #3: `original_filename` May Be Lost
**Location:** State management  
**Problem:** `original_filename` might not be set before `derive_dataset_slug()` is called

---

## ✅ Solution: Preserve Original Filename BEFORE Transformation

### Current Flow (BROKEN):
```
1. User uploads: tips.csv
2. save_upload() transforms: 1762000000_uploaded.csv  ❌ Original name lost!
3. derive_dataset_slug() sees: "1762000000_uploaded.csv"
4. Extracts: "uploaded"
5. Creates folder: uploaded/20251101_HHMMSS/
```

### Fixed Flow (CORRECT):
```
1. User uploads: tips.csv
2. Extract original_filename: "tips.csv"  ✅ BEFORE transformation
3. save_upload() transforms: 1762000000_uploaded.csv
4. derive_dataset_slug(display_name="tips.csv")  ✅ Pass original name!
5. Extracts: "tips"
6. Creates folder: tips/20251101_HHMMSS/  ✅
```

---

## 🔧 Required Fix

### Location: `agent.py` line ~4145 (file upload detection)

**Add this BEFORE `save_upload()` call:**

```python
# CRITICAL: Preserve original filename from blob BEFORE save_upload transforms it
original_user_filename = None
if hasattr(part, 'inline_data') and hasattr(part.inline_data, 'display_name'):
    original_user_filename = part.inline_data.display_name
    logger.info(f"[UPLOAD] Original filename from blob: {original_user_filename}")
    # Store in state IMMEDIATELY
    callback_context.state["original_user_filename"] = original_user_filename

# Now call save_upload (which will transform filename)
file_metadata = save_upload(...)

# Pass original_user_filename to derive_dataset_slug
slug = derive_dataset_slug(
    state,
    headers=headers,
    filepath=file_metadata['file_id'],  # Transformed path
    display_name=original_user_filename  # ← Original name from blob!
)
```

---

## 📝 Alternative: Check `large_data_handler.save_upload()`

The `save_upload()` function might already have access to the original filename but not returning it. Check if we can:

1. Preserve `display_name` in `save_upload()`
2. Return it in the file metadata dict
3. Use it in `derive_dataset_slug()`

---

## 🧹 Cleanup Required

After fix is applied and tested, delete the orphaned folders:

```powershell
cd C:\harfile\data_science_agent\data_science\.uploaded\_workspaces

# Delete legacy hash-based folders (OLD)
Remove-Item student_portuguese_clean_utf8_e117a84f -Recurse -Force
Remove-Item student_portuguese_clean_6af3b204 -Recurse -Force
Remove-Item ads50_utf8_22edc448 -Recurse -Force
Remove-Item ads50_9d536f2c -Recurse -Force
Remove-Item default -Recurse -Force
Remove-Item _global -Recurse -Force

# Consolidate "uploaded" folders
# (Manual review needed - check which ones have actual data)
# Then rename the "uploaded" folder to the actual dataset name
```

---

## 🎯 Expected Result After Fix

```
.uploaded/_workspaces/
  ├─ tips/
  │   └─ 20251101_HHMMSS/  ✅ All tips.csv uploads go here
  ├─ iris/
  │   └─ 20251101_HHMMSS/  ✅ All iris.csv uploads go here
  ├─ ads50/
  │   └─ 20251101_151122/  ✅ (already correct)
  └─ student_portuguese_clean/
      └─ 20251101_160123/  ✅ (already correct)
```

**No more `uploaded/{timestamp}/` folders!**

---

## 📊 Summary

| Component | Status | Issue |
|-----------|--------|-------|
| Workspace structure | ✅ Correct | `{dataset}/{run_id}/` pattern works |
| Dataset name from `display_name` | ⚠️ Partial | Sometimes empty/missing |
| Dataset name from filename | ❌ Broken | Filename already transformed |
| Fallback to "uploaded" | ⚠️ Creates duplicates | Each upload = new folder |

**Root Cause:** Original filename lost before `derive_dataset_slug()` is called.

**Fix:** Preserve `display_name` from blob BEFORE `save_upload()` transforms the filename.

---

## ⚠️ Action Required

1. ✅ Review `large_data_handler.save_upload()` - Does it have access to original filename?
2. ✅ Modify upload detection in `agent.py` to preserve `display_name` BEFORE transformation
3. ✅ Pass preserved `display_name` to `derive_dataset_slug()`
4. ✅ Test with new upload
5. ✅ Verify only ONE folder created per dataset
6. ✅ Cleanup old `uploaded/` timestamp folders

---

**Last Updated:** 2025-11-01  
**Status:** ⚠️ PARTIALLY WORKING - FIX REQUIRED  
**Impact:** Medium (creates clutter, but doesn't break functionality)

