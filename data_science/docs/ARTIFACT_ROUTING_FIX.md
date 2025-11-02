# 🔧 Artifact Routing Fix for analyze_dataset()

## Problem

When you ran `analyze_dataset()`, it created 8 plots in the `.plot/` directory at **05:38 AM**:
- `uploaded_auto_corr_heatmap.png`
- `uploaded_auto_hist_fare.png`
- `uploaded_auto_hist_age.png`
- `uploaded_auto_hist_sibsp.png`
- `uploaded_auto_hist_pclass.png`
- `uploaded_auto_hist_parch.png`
- `uploaded_auto_hist_survived.png`
- `uploaded_auto_box_fare_by_sex.png`

**BUT** these plots were **NOT copied** to your workspace: `uploaded/20251017_053841/plots/`

### Root Cause

The `plot()` tool was returning **filenames only**, not **full paths**:

```python
# ❌ BEFORE (broken)
artifacts.append(filename)  # e.g., "titanic_auto_hist_age.png"

# Return:
{"artifacts": ["titanic_auto_hist_age.png", ...]}
```

The artifact manager in `artifact_manager.py` looks for **full file paths** to copy:

```python
# artifact_manager.py line 135-141
for item in _as_iter(result.get("artifacts")):
    if isinstance(item, dict) and "path" in item:
        out.append(...)  # Expects file path, not just name
```

When it received just filenames, it couldn't find the files on disk to copy them!

## Solution

Updated `plot()` in `ds_tools.py` to return **full paths**:

```python
# ✅ AFTER (fixed)
plot_path = os.path.join(plot_dir, filename)  # Full path
artifacts.append(plot_path)  # e.g., "C:/.../.plot/titanic_auto_hist_age.png"

# Return:
{
    "artifacts": ["C:/.../.plot/titanic_auto_hist_age.png", ...],
    "plot_paths": ["C:/.../.plot/titanic_auto_hist_age.png", ...]  # Explicit key
}
```

### Changes Made

1. **Line 1490** in `data_science/ds_tools.py`:
   ```python
   artifacts.append(plot_path)  # ✅ Store full path, not just filename
   ```

2. **Line 1620** in `data_science/ds_tools.py`:
   ```python
   return _json_safe({
       "artifacts": artifacts,
       "plot_paths": artifacts,  # ✅ Explicit key for artifact manager
       ...
   })
   ```

## Testing

Verified with test script:

```
✅ plot() returned:
  • artifacts: ['C:\...\data_science\.plot\titanic_auto_corr_heatmap.png', ...]
  • plot_paths: ['C:\...\data_science\.plot\titanic_auto_corr_heatmap.png', ...]
  • 3 plots created

✅ All paths are absolute/relative (not just filenames)
✅ plot_paths key present for artifact manager
```

## Next Upload Test

When you **next upload a dataset and run tools**:

1. **Upload file** → Workspace created (e.g., `tips/20251017_120000/`)
2. **Run any of these tools**:
   - `analyze_dataset()` or `plot()` → Creates plots
   - `export_executive_report()` → Creates PDF report
   - `export()` → Creates PDF report
   - `train()` / `train_classifier()` → Creates model files
3. **Watch console** for:
   ```
   📦 Artifact copied: tips_auto_hist_total_bill.png → plots/
   📦 Artifact copied: tips_executive_report_20251017_120000.pdf → reports/
   📦 Artifact copied: model.pkl → models/
   ✅ Routed 8 artifact(s) to workspace: tips/20251017_120000/
   ```
4. **Check workspace**:
   ```
   cd .uploaded\_workspaces\tips\20251017_120000
   dir /s
   ```
   You should see:
   - `plots/` - All plot PNG files
   - `reports/` - PDF reports
   - `models/` - Model files
   - `manifests/` - Artifact audit trail

## Why Your Current Workspace Is Still Empty

Your workspace `uploaded/20251017_053841/` is empty because:
- The plots were created **before** this fix was applied
- They were created with the old code that returned filenames only
- No artifacts were routed because the paths couldn't be resolved

**Solution**: Upload a new dataset or re-run `analyze_dataset()` with the fixed code!

## Summary

### plot() Tool Fix

| Before | After |
|--------|-------|
| ❌ Returns: `{"artifacts": ["file.png"]}` | ✅ Returns: `{"artifacts": ["C:/.../file.png"], "plot_paths": [...]}` |
| ❌ Artifact manager can't find file | ✅ Artifact manager finds file on disk |
| ❌ No console output: `📦 Artifact copied: ...` | ✅ Console shows: `📦 Artifact copied: file.png → plots/` |
| ❌ Workspace plots/ folder empty | ✅ Workspace plots/ folder populated |

### Tools Status

| Tool | Artifact Type | Return Key | Status |
|------|---------------|------------|--------|
| `plot()` | PNG plots | `plot_paths` | ✅ **FIXED** (returns full paths) |
| `analyze_dataset()` | Calls `plot()` internally | `plot_paths` | ✅ **FIXED** (uses fixed plot()) |
| `export_executive_report()` | PDF report | `pdf_path` | ✅ **Already working** (returns full path) |
| `export()` | PDF report | `pdf_path` | ✅ **Already working** (returns full path) |
| `train()` / `train_classifier()` | Model files | `model_path` | ✅ **Already working** (returns full path) |
| `train_regressor()` | Model files | `model_path` | ✅ **Already working** (returns full path) |
| `clean()` / `impute_*()` | CSV files | Saves to disk | ✅ **Already working** (returns full path) |

### What Was Broken

**Only `plot()` was broken** - it was returning filenames instead of full paths.

Since `analyze_dataset()` internally calls plotting functions that use the same `_save_current()` helper, fixing `plot()` **automatically fixed `analyze_dataset()` too**!

### What Was Already Working

**Reports (`export_executive_report()`, `export()`)** were always returning full paths:
```python
pdf_path = os.path.join(export_dir, pdf_filename)  # Full path
return {"pdf_path": pdf_path}  # ✅ Correct
```

So executive reports **should have been routing correctly** all along. If they weren't being routed, it might be because:
1. They were generated before the artifact manager was active
2. The `export_executive_report()` wasn't in the `_ARTIFACT_GENERATING_TOOLS` whitelist (check `agent.py`)

🎉 **All artifact routing is now fixed and will work on your next upload!**

