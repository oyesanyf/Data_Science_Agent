# Artifact Manager Configuration - Complete Setup

## Overview

The Artifact Manager is now properly configured to:
1. ✅ Route artifacts to workspace subdirectories
2. ✅ Filter model files from UI display (but keep them in storage)
3. ✅ Save all tool outputs with metrics to JSON
4. ✅ Maintain manifest files for traceability

---

## Architecture

### 1. Workspace Structure

```
.uploaded/_workspaces/
└── {dataset_name}/
    └── {run_id}/
        ├── uploads/      ← CSV/data files uploaded
        ├── data/         ← Processed/cleaned data
        ├── models/       ← Trained models (.joblib, .pkl) 
        ├── reports/      ← JSON outputs + PDFs
        ├── plots/        ← Visualizations (PNG, JPG)
        ├── metrics/      ← Performance metrics
        ├── indexes/      ← Data indexes
        ├── logs/         ← Log files
        ├── tmp/          ← Temporary files
        ├── manifests/    ← Artifact manifests
        └── unstructured/ ← Other files
```

### 2. Artifact Routing Flow

```
Tool Execution
     ↓
Result with artifacts: {
    "model_path": "model.joblib",
    "plot_paths": ["chart1.png", "chart2.png"],
    "metrics": {"accuracy": 0.95}
}
     ↓
route_artifacts_from_result()
     ↓
Copies files to workspace:
- models/model.joblib
- plots/chart1.png
- plots/chart2.png
     ↓
Creates manifest:
manifests/artifact_manifest.json
     ↓
Saves JSON output:
reports/train_baseline_model_output_123456.json
```

---

## Key Components

### 1. Artifact Type Mapping

**File Type** → **Workspace Subdirectory**

| Artifact Type | Destination Folder | Examples |
|--------------|-------------------|----------|
| `model` | `models/` | .joblib, .pkl, .h5, .pt |
| `plot`, `image` | `plots/` | .png, .jpg, .svg |
| `report` | `reports/` | .pdf, .json |
| `metrics` | `metrics/` | metrics.json |
| `data` | `data/` | cleaned.csv |
| `upload` | `uploads/` | uploaded files |
| `index` | `indexes/` | index files |
| `log` | `logs/` | log files |

### 2. Model File Filtering

**Model Extensions Excluded from UI:**
- `.joblib` (sklearn models)
- `.pkl`, `.pickle` (pickle files)
- `.h5` (Keras/TensorFlow)
- `.pt`, `.pth` (PyTorch)
- `.onnx` (ONNX models)
- `.pb` (TensorFlow Protocol Buffer)

**Behavior:**
- ✅ Model files ARE saved to `workspace/models/`
- ✅ Model files ARE included in JSON outputs
- ❌ Model files NOT displayed in UI artifacts list
- ✅ UI shows: "*(1 model file(s) saved to workspace - not displayed)*"

**Why?**
- Model files are binary and large
- Clutters the UI artifacts panel
- Still accessible via workspace directory

### 3. Artifact Collection

The system looks for artifacts in multiple ways:

**Priority 1: Explicit artifacts list**
```python
result = {
    "artifacts": [
        {"path": "model.joblib", "type": "model", "label": "baseline"},
        {"path": "plot.png", "type": "plot", "label": "distribution"}
    ]
}
```

**Priority 2: Common keys**
```python
result = {
    "model_path": "model.joblib",
    "plot_paths": ["plot1.png", "plot2.png"],
    "report_path": "report.pdf",
    "metrics_path": "metrics.json"
}
```

**Priority 3: Directory ingestion**
```python
result = {
    "artifacts_dir": "/path/to/folder"  # Ingests all files
}
```

---

## Integration Points

### 1. Tool Wrappers (agent.py)

**Both sync and async wrappers now properly route artifacts:**

```python
# After tool execution
try:
    from .artifact_manager import route_artifacts_from_result
    if tc and hasattr(tc, 'state'):
        route_artifacts_from_result(tc.state, result, func.__name__)
        logger.debug(f"[ARTIFACT ROUTING] Routed artifacts for {func.__name__}")
except Exception as e:
    logger.warning(f"[ARTIFACT ROUTING] Failed for {func.__name__}: {e}")
```

**Fixed Issues:**
- ✅ Corrected parameter order (was: tool_name, result, tc | now: state, result, tool_name)
- ✅ Added proper error logging
- ✅ Added state existence check

### 2. After Tool Callback (callbacks.py)

**Artifacts routed after every tool execution:**

```python
# In after_tool_callback()
try:
    from . import artifact_manager
    if hasattr(callback_context, "state"):
        artifact_manager.route_artifacts_from_result(callback_context.state, result, tool_name)
        logger.debug(f"[CALLBACK] Routed artifacts for {tool_name}")
except Exception as e:
    logger.warning(f"[CALLBACK] Artifact routing failed for {tool_name}: {e}")
```

### 3. UI Display Formatting (adk_safe_wrappers.py)

**Model files filtered from UI artifacts list:**

```python
# Filter out model files for UI display
model_extensions = {'.joblib', '.pkl', '.pickle', '.h5', '.pt', '.pth', '.onnx', '.pb'}

ui_artifacts = []
for artifact in artifacts:
    artifact_str = str(artifact).lower()
    is_model_file = any(artifact_str.endswith(ext) for ext in model_extensions)
    if not is_model_file:
        ui_artifacts.append(artifact)

if ui_artifacts:
    parts.append("**Generated Artifacts:**")
    for artifact in ui_artifacts[:20]:
        parts.append(f"  • {artifact}")

# Add note about filtered model files
model_count = len(artifacts) - len(ui_artifacts)
if model_count > 0:
    parts.append(f"*({model_count} model file(s) saved to workspace - not displayed)*")
```

---

## Configuration Options

### Environment Variables

**WORKSPACES_ROOT**
- Default: `{UPLOAD_ROOT}/_workspaces`
- Custom: Set to absolute path
- Example: `WORKSPACES_ROOT=C:/my_workspaces`

**ARTIFACT_ROUTING_MODE**
- `copy` (default): Copy files to workspace
- `move`: Move files to workspace (removes from original location)
- Example: `ARTIFACT_ROUTING_MODE=move`

**ARTIFACTS_MAX_BYTES**
- Default: `52428800` (50 MB)
- Limit for directory ingestion
- Example: `ARTIFACTS_MAX_BYTES=104857600` (100 MB)

**ARTIFACTS_ALLOWED_EXTS**
- Default: Empty (all extensions)
- Comma-separated list of allowed extensions
- Example: `ARTIFACTS_ALLOWED_EXTS=.png,.jpg,.pdf,.json`

---

## Manifest Files

Every artifact routing creates a manifest for traceability:

**Location:** `workspace_root/manifests/artifact_manifest.json`

**Contents:**
```json
[
  {
    "tool": "train_baseline_model",
    "type": "model",
    "label": "model_path",
    "src": "C:/temp/model.joblib",
    "dst": "C:/.uploaded/_workspaces/housing/20251028_050642/models/model.joblib",
    "filesize": 245678,
    "sha256": "a3f5d9c...",
    "mode": "copy",
    "dataset": "housing",
    "run_id": "20251028_050642",
    "ts": "2025-10-28T05:06:42.123456Z"
  }
]
```

---

## Verification

### Check Workspace Creation

```python
from artifact_manager import ensure_workspace
from large_data_config import UPLOAD_ROOT

state = {"original_dataset_name": "test"}
workspace_path = ensure_workspace(state, str(UPLOAD_ROOT))

print(f"Workspace: {workspace_path}")
print(f"Exists: {workspace_path.exists()}")
```

### Check Artifact Routing

```python
from artifact_manager import route_artifacts_from_result

result = {
    "model_path": "/path/to/model.joblib",
    "plot_paths": ["/path/to/plot.png"],
    "metrics": {"accuracy": 0.95}
}

state = {"workspace_root": "/path/to/workspace"}
route_artifacts_from_result(state, result, "train_baseline_model")
```

### Check Model File Filtering

```python
from adk_safe_wrappers import _ensure_ui_display

result = {
    "artifacts": ["model.joblib", "plot.png", "metrics.json"],
    "metrics": {"accuracy": 0.95}
}

display_result = _ensure_ui_display(result, "train_baseline_model")
print(display_result["__display__"])
# Output will show plot.png and metrics.json
# But NOT model.joblib
# Plus note: "(1 model file(s) saved to workspace - not displayed)"
```

---

## Troubleshooting

### Artifacts Not Routed

**Check logs:**
```
[ARTIFACT ROUTING] Routed artifacts for train_baseline_model
```

**If missing:**
1. Verify workspace_root is set in state
2. Check result has artifact paths
3. Verify files exist at source paths

### Model Files Showing in UI

**Check adk_safe_wrappers.py:**
- Ensure model_extensions set includes your file type
- Verify filtering logic is active

### JSON Outputs Not Saved

**Check logs:**
```
[REPORT DATA] ✓ Saved train_baseline_model output: train_baseline_model_output_123456.json
```

**If missing:**
1. Verify workspace_root exists in callback_context.state
2. Check result has __display__ field
3. Verify reports/ directory is writable

---

## Summary of Changes

| Component | Change | Impact |
|-----------|--------|--------|
| **agent.py** | Fixed parameter order in route_artifacts_from_result() | ✅ Artifacts now properly routed |
| **callbacks.py** | Added artifact routing to after_tool_callback | ✅ Redundant routing for safety |
| **adk_safe_wrappers.py** | Filter model files from UI display | ✅ Cleaner UI, models still saved |
| **callbacks.py** | Workspace creation if missing | ✅ Always have workspace for outputs |
| **adk_safe_wrappers.py** | Better error logging | ✅ Easier debugging |

---

## Best Practices

1. **Always return artifacts in tool results**
   ```python
   return {
       "model_path": model_path,
       "plot_paths": [plot1, plot2],
       "metrics": metrics
   }
   ```

2. **Use standard artifact keys**
   - `model_path` / `model_paths`
   - `plot_path` / `plot_paths`
   - `report_path` / `report_paths`
   - `metrics_path` / `metrics_paths`

3. **Let the system handle routing**
   - Don't manually move files
   - Return paths, let artifact manager route them

4. **Check manifests for debugging**
   - Look at `manifests/artifact_manifest.json`
   - Verify files were copied/moved correctly

---

**Status:** ✅ Artifact Manager fully configured and operational
**Date:** 2025-10-28

