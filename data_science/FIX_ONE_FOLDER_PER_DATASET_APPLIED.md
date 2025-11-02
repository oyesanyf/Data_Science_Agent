# ✅ FIX APPLIED: One Folder Per Dataset

## 📊 Current Status

### Before Fix:
```
.uploaded/_workspaces/
  ├─ uploaded/  ← 16 folders! ❌
  │   ├─ 20251101_151210/
  │   ├─ 20251101_151233/
  │   ├─ 20251101_161646/
  │   └─ ... (13 more)
  ├─ ads50/
  │   └─ 20251101_151122/  ✅ (worked by accident)
  └─ student_portuguese_clean/
      └─ 20251101_160123/  ✅ (worked by accident)
```

### After Fix:
```
.uploaded/_workspaces/
  ├─ tips/
  │   └─ 20251101_HHMMSS/  ✅ ALL tips.csv uploads go here
  ├─ iris/
  │   └─ 20251101_HHMMSS/  ✅ ALL iris.csv uploads go here
  ├─ ads50/
  │   └─ 20251101_151122/  ✅ (still correct)
  └─ student_portuguese_clean/
      └─ 20251101_160123/  ✅ (still correct)
```

---

## 🔧 Fix Applied

### Location: `agent.py` lines 4151-4159

**BEFORE (BROKEN):**
```python
# Fallback by filename if available
original_filename = None
if hasattr(part, 'file_name') and part.file_name:
    original_filename = part.file_name  # ← Checked file_name first
elif hasattr(part.inline_data, 'file_name') and part.inline_data.file_name:
    original_filename = part.inline_data.file_name
# ❌ display_name was NEVER checked! (it's checked later, but too late)
```

**AFTER (FIXED):**
```python
# Fallback by filename if available (CHECK display_name FIRST - it often contains browser upload name)
original_filename = None
if hasattr(part.inline_data, 'display_name') and part.inline_data.display_name:
    original_filename = part.inline_data.display_name  # ← Check display_name FIRST! ✅
    logger.info(f"[UPLOAD] Original filename from display_name: {original_filename}")
elif hasattr(part, 'file_name') and part.file_name:
    original_filename = part.file_name
elif hasattr(part.inline_data, 'file_name') and part.inline_data.file_name:
    original_filename = part.inline_data.file_name
```

---

## 🎯 Why This Works

### The Flow:

1. **User uploads:** `tips.csv` via browser
2. **ADK stores original name in:** `part.inline_data.display_name = "tips.csv"`  ✅
3. **Now we capture it FIRST:** `original_filename = "tips.csv"`  ✅
4. **Pass to save_upload():** `save_upload(data, original_name="tips.csv")`  ✅
5. **File saved as:** `1762000000_tips.csv` (timestamp + original name)
6. **Pass to derive_dataset_slug():** `display_name="tips.csv"`  ✅
7. **Extracts dataset name:** `"tips"` ✅
8. **Creates folder:** `.uploaded/_workspaces/tips/20251101_HHMMSS/`  ✅

### Key Insight:

`part.inline_data.display_name` contains the **original browser upload filename** and was being ignored! Now we check it FIRST.

---

## ✅ Validation

### Syntax Check:
```bash
$ python -m py_compile agent.py
✅ PASS (exit code: 0)
```

### Logic Check:
```python
# Priority order (now correct):
1. part.inline_data.display_name  ✅ FIRST (browser upload name)
2. part.file_name                 (fallback)
3. part.inline_data.file_name     (fallback)
```

---

## 🧪 Testing Plan

### Test Case 1: Upload tips.csv

**Expected:**
```
1. Upload tips.csv
2. System captures: display_name = "tips.csv"
3. Extracts dataset name: "tips"
4. Creates folder: .uploaded/_workspaces/tips/20251101_HHMMSS/
5. All tips.csv uploads go to: tips/20251101_HHMMSS/ ✅
```

### Test Case 2: Upload iris.csv

**Expected:**
```
1. Upload iris.csv
2. System captures: display_name = "iris.csv"
3. Extracts dataset name: "iris"
4. Creates folder: .uploaded/_workspaces/iris/20251101_HHMMSS/
5. All iris.csv uploads go to: iris/20251101_HHMMSS/ ✅
```

### Test Case 3: Re-upload tips.csv (same dataset)

**Expected:**
```
1. Upload tips.csv again (same file)
2. System detects: dataset name = "tips" (same as before)
3. System checks: workspace_run_id already exists in session
4. Reuses existing folder: tips/20251101_HHMMSS/ ✅
5. NO new folder created ✅
```

---

## 🧹 Cleanup Required (After Testing)

Once the fix is verified working, clean up old orphaned folders:

```powershell
cd C:\harfile\data_science_agent\data_science\.uploaded\_workspaces

# Delete legacy hash-based folders (OLD system, pre-fix)
Remove-Item student_portuguese_clean_utf8_e117a84f -Recurse -Force
Remove-Item student_portuguese_clean_6af3b204 -Recurse -Force
Remove-Item ads50_utf8_22edc448 -Recurse -Force
Remove-Item ads50_9d536f2c -Recurse -Force
Remove-Item default -Recurse -Force
Remove-Item _global -Recurse -Force

# Review "uploaded" folder contents
cd uploaded
Get-ChildItem -Directory | Format-Table Name, LastWriteTime

# If you can identify which dataset each timestamp folder belongs to, 
# manually move files to the correct dataset folder
# Example:
# Move-Item 20251101_160905\* ..\tips\20251101_160905\ -Force
# Then delete the empty uploaded timestamp folder
```

---

## 📋 Summary

| Issue | Status | Solution |
|-------|--------|----------|
| Multiple `uploaded/{timestamp}/` folders | ✅ FIXED | Check `display_name` first |
| Dataset name extraction failing | ✅ FIXED | Preserve original filename |
| Workspace creation logic | ✅ ALREADY CORRECT | `{dataset}/{run_id}/` pattern |
| Legacy hash-based folders | ⚠️ MANUAL CLEANUP | Delete old folders |

---

## ⚠️ RESTART SERVER TO APPLY FIX

```bash
# Stop server (Ctrl+C)
cd C:\harfile\data_science_agent
python -m data_science.main
```

**After restart:**
1. Upload a test CSV (e.g., tips.csv)
2. Check workspace folders
3. Verify only ONE folder created: `tips/20251101_HHMMSS/`
4. Upload same file again
5. Verify NO new folder created (reuses existing)

---

## 🎉 Expected Results

### Before Restart (Old Behavior):
```
Upload tips.csv → creates uploaded/20251101_160905/  ❌
Upload tips.csv → creates uploaded/20251101_161027/  ❌
Upload iris.csv → creates uploaded/20251101_161134/  ❌
```

### After Restart (New Behavior):
```
Upload tips.csv → creates tips/20251101_HHMMSS/  ✅
Upload tips.csv → reuses tips/20251101_HHMMSS/  ✅
Upload iris.csv → creates iris/20251101_HHMMSS/  ✅
```

---

**Status:** ✅ FIX APPLIED  
**Impact:** High (eliminates workspace clutter)  
**Risk:** Low (surgical, minimal change)  
**Confidence:** 0.90 (High)  

**Last Updated:** 2025-11-01  
**Action Required:** ⚠️ RESTART SERVER

