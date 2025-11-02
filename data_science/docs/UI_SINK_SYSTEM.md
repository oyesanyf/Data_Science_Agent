# UI Sink System

## Overview

The UI Sink System is a centralized architecture for automatically converting tool outputs into a live, user-friendly Markdown page that updates after every tool execution. This provides a unified, polished user experience where all tool results—tables, summaries, plots, and artifacts—appear in one scrolling "Session UI Page" visible in the Artifacts panel.

## Architecture

```
Tool Execution
     ↓
after_tool_callback (callbacks.py)
     ↓
_as_blocks() → Convert result to UI blocks
     ↓
publish_ui_blocks() → Append to session_ui_page.md
     ↓
save_ui_event() → Persist to SQLite
     ↓
save_tool_execution() → Track execution history
     ↓
Artifacts Panel (session_ui_page.md)
```

## Components

### 1. `data_science/ui_page.py`
**Purpose**: Manages the live Markdown page that serves as the UI canvas.

**Key Functions**:
- `ensure_ui_page(ctx)`: Creates/locates the session UI page
- `publish_ui_blocks(ctx, tool_name, blocks)`: Appends UI blocks to the page
- `append_section(ctx, title, body_md)`: Adds a markdown section
- `append_table(ctx, title, rows)`: Adds a markdown table
- `append_artifact_list(ctx, title, filenames)`: Adds artifact links

**Output**: `session_ui_page.md` in the workspace docs directory

### 2. `data_science/state_store.py`
**Purpose**: SQLite-backed persistence for UI events and session data.

**Database Tables**:
- `ui_events`: Stores all UI block publications
- `sessions`: Tracks session metadata and activity
- `tool_executions`: Complete execution history with timing

**Key Functions**:
- `init_db()`: Initialize database schema
- `save_ui_event(session_id, tool_name, blocks)`: Persist UI event
- `save_tool_execution(...)`: Track tool execution metrics
- `get_session_stats(session_id)`: Retrieve session analytics
- `cleanup_old_sessions(days)`: Auto-cleanup old data

**Database Location**: `data_science/adk_state.db` (configurable via `STATE_DB_PATH`)

### 3. `data_science/callbacks.py`
**Purpose**: Integrates UI sink into the agent's tool execution lifecycle.

**Key Functions**:
- `_as_blocks(tool_name, result)`: Heuristic converter from tool results to UI blocks
- `after_tool_callback(...)`: Main callback that publishes to UI after each tool

**Conversion Heuristics**:
- `ui_text`, `message`, `content`, `summary` → Markdown section
- `table_rows` (list of lists) → Markdown table
- `table_csv` (CSV string) → Markdown table
- `artifacts`, `plots`, `artifact_names` → Artifact list with links
- `metrics` (dict) → Metrics table
- `ui_blocks` (explicit) → Direct passthrough (no heuristic)

## UI Block Schema

Tools can return results in a standard format that the UI sink automatically converts:

### Standard Result Format
```python
{
    "status": "success",
    "ui_text": "Analysis complete. Found 3 outliers.",
    "table_rows": [
        ["Column", "Mean", "Std"],
        ["age", "35.2", "12.4"],
        ["income", "65000", "15000"]
    ],
    "artifacts": ["plot_1.png", "report.pdf"],
    "metrics": {
        "accuracy": 0.95,
        "f1_score": 0.92
    }
}
```

### Explicit UI Blocks (Advanced)
For precise control, tools can return `ui_blocks` directly:

```python
{
    "status": "success",
    "ui_blocks": [
        {
            "type": "markdown",
            "title": "Analysis Summary",
            "content": "## Key Findings\n\n- Finding 1\n- Finding 2"
        },
        {
            "type": "table",
            "title": "Top Features",
            "rows": [
                ["Feature", "Importance"],
                ["age", "0.45"],
                ["income", "0.32"]
            ]
        },
        {
            "type": "artifact_list",
            "title": "Generated Plots",
            "files": ["dist_target.png", "corr_heatmap.png"]
        }
    ]
}
```

## Block Types

### 1. Markdown Block
```python
{
    "type": "markdown",
    "title": "Section Title",
    "content": "Markdown content here..."
}
```

### 2. Table Block
```python
{
    "type": "table",
    "title": "Table Title",
    "rows": [
        ["Header1", "Header2"],  # First row is header
        ["Value1", "Value2"],    # Subsequent rows are data
        ["Value3", "Value4"]
    ]
}
```

### 3. Artifact List Block
```python
{
    "type": "artifact_list",
    "title": "Files",
    "files": ["file1.png", "file2.pdf", "report.html"]
}
```

## Usage Examples

### Example 1: Simple Tool Result
```python
def analyze_data_tool(csv_path: str) -> dict:
    # ... analysis logic ...
    return {
        "status": "success",
        "ui_text": f"Analyzed {rows} rows and {cols} columns.",
        "metrics": {
            "rows": rows,
            "columns": cols,
            "missing_pct": missing_pct
        }
    }
```

**UI Output**:
```markdown
### 🔧 analyze_data_tool @ 2025-10-22 18:30:45

## Summary

Analyzed 1000 rows and 15 columns.

## Metrics

| Metric | Value |
| --- | --- |
| rows | 1000 |
| columns | 15 |
| missing_pct | 2.5 |
```

### Example 2: Rich Tool Result
```python
def train_model_tool(target: str) -> dict:
    # ... training logic ...
    return {
        "status": "success",
        "ui_blocks": [
            {
                "type": "markdown",
                "title": "Training Complete",
                "content": f"**Model**: LightGBM\n**Target**: {target}\n**Accuracy**: {acc:.2%}"
            },
            {
                "type": "table",
                "title": "Feature Importance",
                "rows": [["Feature", "Importance"]] + feature_rows
            },
            {
                "type": "artifact_list",
                "title": "Model Artifacts",
                "files": ["model.pkl", "feature_importance.png", "confusion_matrix.png"]
            }
        ]
    }
```

## Benefits

### 1. **Unified UX**
- All tool outputs appear in one scrolling page
- Consistent formatting across all tools
- Easy to scan and review session history

### 2. **Zero Coupling**
- Tools just return data
- UI sink handles all presentation logic
- No need to modify existing tools

### 3. **Persistent History**
- SQLite stores all UI events
- Can rebuild the page after restarts
- Enables session analytics and debugging

### 4. **Automatic Artifact Linking**
- Artifacts are automatically linked in the UI
- No manual artifact management needed
- Files are accessible via Artifacts panel

### 5. **Graceful Degradation**
- If UI sink fails, tools still work normally
- Errors are logged but don't break execution
- System continues even if SQLite is unavailable

## Configuration

### Environment Variables

- `STATE_DB_PATH`: Path to SQLite database (default: `data_science/adk_state.db`)
- `WORKSPACES_ROOT`: Root directory for workspace files (default: `uploads/_workspaces`)

### Customization

To customize the UI page location, modify `ensure_ui_page()` in `ui_page.py`:

```python
def ensure_ui_page(ctx: CallbackContext) -> str:
    # Custom logic to determine page location
    custom_path = "/path/to/custom/location/session_ui_page.md"
    ctx.state["ui_page_path"] = custom_path
    # ... create file if missing ...
    return custom_path
```

## Session Analytics

Retrieve session statistics:

```python
from data_science.state_store import get_session_stats

stats = get_session_stats("session-123")
# Returns:
# {
#     "tool_counts": {"train_model": 3, "plot_data": 5},
#     "total_executions": 8,
#     "successful_executions": 7,
#     "success_rate": 87.5
# }
```

## Maintenance

### Cleanup Old Sessions

Automatically clean up sessions older than 30 days:

```python
from data_science.state_store import cleanup_old_sessions

cleanup_old_sessions(days=30)
```

### Database Backup

The SQLite database can be backed up using standard tools:

```bash
# Backup
cp data_science/adk_state.db data_science/adk_state.db.backup

# Restore
cp data_science/adk_state.db.backup data_science/adk_state.db
```

## Troubleshooting

### UI Page Not Updating

1. Check that `after_tool_callback` is registered in `agent.py`
2. Verify `ui_page.py` and `state_store.py` are importable
3. Check logs for `[UI SINK]` messages
4. Ensure workspace paths are correctly set in state

### SQLite Errors

1. Check file permissions on `data_science/adk_state.db`
2. Verify disk space is available
3. Check logs for database initialization errors
4. Try deleting the database file to recreate it

### Missing Artifacts in UI

1. Verify artifacts are returned in tool result
2. Check that artifact files exist on disk
3. Ensure artifact paths are relative or absolute
4. Check `[CALLBACK]` logs for artifact push messages

## Future Enhancements

- **Live Streaming**: Real-time updates via WebSocket
- **Interactive Widgets**: Clickable charts and tables
- **Export Options**: PDF, HTML, or JSON export
- **Session Replay**: Replay entire sessions from SQLite
- **Dashboard View**: Aggregate analytics across sessions
- **Custom Themes**: User-configurable UI styling

## See Also

- `data_science/callbacks.py`: Callback implementation
- `data_science/artifact_manager.py`: Artifact management
- `data_science/utils_state.py`: State management helpers
- `INTERACTIVE_WORKFLOW_GUIDE.md`: Interactive workflow documentation

