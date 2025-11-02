# 🔧 FIXES APPLIED - Workspace Duplication

## Date: Nov 1, 2025 - 8:02 PM

## 🚨 Problem Reported:
Upload "thing.csv" created **3 folders** instead of 1:
```
thing/                    ← CORRECT ✅
thing_863cc374/           ← hash-based ❌
thing_utf8_a89ac9cf/      ← hash-based ❌
```

---

## ✅ ROOT CAUSES IDENTIFIED:

### 1. Hash Suffixes in `utils/paths.py`
**File:** `utils/paths.py` line 22-27  
**Problem:** `_slugify()` was adding SHA1 hash suffixes to folder names

**BEFORE:**
```python
def _slugify(name: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("_").lower()
    h = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return f"{name[:48]}_{h}" if name else h  # ← Added hash!
```

**AFTER:**
```python
def _slugify(name: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("_").lower()
    # NO HASH - return clean name only
    return name[:48] if name else "dataset"  # ← Clean name!
```

---

### 2. Old 4-Folder Structure in `utils/paths.py`
**File:** `utils/paths.py` line 38-44  
**Problem:** `workspace_dir()` was creating OLD structure (4 folders) instead of NEW structure (12 folders)

**BEFORE:**
```python
def workspace_dir(dataset_slug: str) -> Path:
    d = WORKSPACES_ROOT / dataset_slug
    (d / "plots").mkdir(parents=True, exist_ok=True)
    (d / "models").mkdir(parents=True, exist_ok=True)
    (d / "artifacts").mkdir(parents=True, exist_ok=True)  # Wrong!
    (d / "cache").mkdir(parents=True, exist_ok=True)      # Wrong!
    return d
```

**AFTER:**
```python
def workspace_dir(dataset_slug: str) -> Path:
    d = WORKSPACES_ROOT / dataset_slug
    # Use SAME 12 folders as artifact_manager.py
    subdirs = [
        "uploads", "data", "models", "reports", "results",
        "plots", "metrics", "indexes", "logs", "tmp", "manifests", "unstructured"
    ]
    for subdir in subdirs:
        (d / subdir).mkdir(parents=True, exist_ok=True)
    return d
```

---

## 📊 EXPECTED RESULT:

### Upload "mydata.csv":

**BEFORE (3 folders created):**
```
mydata/               ← artifact_manager
mydata_abc12345/      ← utils/paths (hash suffix)
mydata_utf8_xyz789/   ← utils/paths (hash suffix + encoding)
```

**AFTER (1 folder created):**
```
mydata/               ← Clean name, no hash! ✅
  ├─ uploads/
  ├─ data/
  ├─ models/
  ├─ reports/
  ├─ results/
  ├─ plots/
  ├─ metrics/
  ├─ indexes/
  ├─ logs/
  ├─ tmp/
  ├─ manifests/
  └─ unstructured/
```

---

## ⚠️ CRITICAL: SERVER RESTART REQUIRED!

These changes will NOT take effect until you restart the server:

```powershell
# Stop server (Ctrl+C)
# Restart:
python -m data_science.main
```

---

## 🧹 CLEANUP AFTER RESTART:

Delete all old hash-based folders:

```powershell
cd C:\harfile\data_science_agent\data_science\.uploaded\_workspaces

# Delete hash-based folders
Remove-Item *_[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f] -Recurse -Force
Remove-Item *_utf8_* -Recurse -Force
Remove-Item uploaded -Recurse -Force

# Keep only clean-named folders like:
# - thing/
# - ads50/
# - car_crashes/
```

---

## 📋 TODO List Status:

- [x] ✅ Remove ADK artifact service calls
- [x] ✅ Remove hash suffix from `utils/paths.py`
- [x] ✅ Fix workspace structure in `utils/paths.py`
- [x] ✅ Auto-cleanup uploaded files
- [ ] ⏳ Change recursive auto-discovery to non-recursive
- [ ] ⏳ Add bind guard in rehydrate_session_state
- [ ] ⏳ Test: Upload one file, verify ONE folder

---

## 🎯 Confidence: 95%

**Why:** Fixed both the hash suffix logic AND the workspace structure mismatch.  
**Remaining:** Need to test after server restart.

---

**Status:** 🟢 FIXES READY - RESTART SERVER TO APPLY
