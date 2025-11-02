# Workspace Structure Documentation

## ✅ Verified Correct Structure

The Data Science Agent uses the following workspace structure for organizing all files related to a specific dataset:

```
uploads/_workspaces/<dataset_name>/<timestamp>/
  ├─ uploads/         # Uploaded CSV files
  ├─ data/            # Processed/cleaned data
  ├─ models/          # Trained models (.pkl, .joblib, .onnx)
  ├─ reports/         # Generated reports (PDF, HTML)
  ├─ plots/           # Visualizations (PNG, SVG)
  ├─ metrics/         # Evaluation metrics (JSON, CSV)
  ├─ indexes/         # Vector indexes (FAISS)
  ├─ logs/            # Tool execution logs
  ├─ tmp/             # Temporary files
  ├─ manifests/       # Metadata and manifests
  ├─ unstructured/    # Unstructured data (text, images, etc.)
  └─ session_ui_page.md  # UI Sink live page (NEW!)
```

## Implementation Details

### 1. Workspace Creation
**File**: `data_science/artifact_manager.py`
**Function**: `ensure_workspace(callback_state, upload_root)`

- Creates workspace structure on first file upload
- Uses dataset name from uploaded file (or "uploaded" as fallback)
- Timestamp format: `YYYYMMDD_HHMMSS`
- Creates "latest" symlink pointing to most recent workspace

### 2. UI Sink Integration
**File**: `data_science/ui_page.py`
**Function**: `ensure_ui_page(ctx)`

- **Updated** to use `workspace_root` from state
- Creates `session_ui_page.md` in workspace root
- Follows the correct `uploads/_workspaces/<dataset>/<timestamp>/` structure

### 3. State Storage
**File**: `data_science/state_store.py`
**Database**: `data_science/adk_state.db`

- Stores UI events, sessions, and tool executions
- Independent of workspace structure
- Persists across server restarts

## Example Workspace

When a user uploads `sales_data.csv`:

```
uploads/_workspaces/sales_data/20251021_191500/
  ├─ uploads/
  │   └─ sales_data.csv
  ├─ data/
  │   └─ sales_data_cleaned.csv
  ├─ models/
  │   ├─ lightgbm_model.pkl
  │   └─ xgboost_model.pkl
  ├─ reports/
  │   ├─ executive_summary.pdf
  │   └─ technical_report.pdf
  ├─ plots/
  │   ├─ distribution.png
  │   ├─ correlation_matrix.png
  │   └─ feature_importance.png
  ├─ metrics/
  │   └─ evaluation_metrics.json
  └─ session_ui_page.md  # Live UI with all tool outputs!
```

## Workspace State Management

The workspace paths are stored in the callback context state:

```python
callback_state = {
    "workspace_root": "uploads/_workspaces/sales_data/20251021_191500",
    "workspace_run_id": "20251021_191500",
    "original_dataset_name": "sales_data",
    "workspace_paths": {
        "uploads": "uploads/_workspaces/sales_data/20251021_191500/uploads",
        "data": "uploads/_workspaces/sales_data/20251021_191500/data",
        "models": "uploads/_workspaces/sales_data/20251021_191500/models",
        "reports": "uploads/_workspaces/sales_data/20251021_191500/reports",
        "plots": "uploads/_workspaces/sales_data/20251021_191500/plots",
        "metrics": "uploads/_workspaces/sales_data/20251021_191500/metrics",
        "indexes": "uploads/_workspaces/sales_data/20251021_191500/indexes",
        "logs": "uploads/_workspaces/sales_data/20251021_191500/logs",
        "tmp": "uploads/_workspaces/sales_data/20251021_191500/tmp",
        "manifests": "uploads/_workspaces/sales_data/20251021_191500/manifests",
        "unstructured": "uploads/_workspaces/sales_data/20251021_191500/unstructured"
    }
}
```

## UI Sink Integration

The UI Sink system automatically creates `session_ui_page.md` in the workspace root:

**Location**: `uploads/_workspaces/<dataset>/<timestamp>/session_ui_page.md`

**Content**: Live Markdown page with:
- Tool execution history
- Rich formatted tables
- Metrics displays
- Artifact links
- Timestamps for each tool call

**Persistence**: Also stored in SQLite (`data_science/adk_state.db`) for session replay

## Configuration

### Environment Variables

- `WORKSPACES_ROOT`: Override workspace root (default: `uploads/_workspaces`)
- `STATE_DB_PATH`: Override database path (default: `data_science/adk_state.db`)

### Example Custom Configuration

```bash
export WORKSPACES_ROOT="/data/ml_workspaces"
export STATE_DB_PATH="/data/adk_state.db"
```

This would create workspaces at:
```
/data/ml_workspaces/<dataset>/<timestamp>/
```

## Verification

To verify the workspace structure is working correctly:

1. Upload a CSV file via the ADK UI
2. Run any tool (e.g., `analyze_dataset`)
3. Check that the workspace was created:
   ```bash
   ls -la uploads/_workspaces/
   ```
4. Verify `session_ui_page.md` exists in the workspace root
5. Check the UI Sink database:
   ```bash
   sqlite3 data_science/adk_state.db "SELECT * FROM sessions;"
   ```

## Status

✅ **Workspace structure**: Correctly implemented in `artifact_manager.py`
✅ **UI Sink integration**: Updated to use `workspace_root`
✅ **Database**: Initialized on first tool call
✅ **All subdirectories**: Created automatically on workspace initialization

---

**Last Updated**: 2025-10-21
**Status**: Verified and Tested

