# Workflow State Persistence

## Overview

The workflow system now **persists across server restarts**, ensuring you can resume your data science workflow from exactly where you left off.

## How It Works

### 1. Automatic State Saving

Every time you use `next_stage()` or `back_stage()`, the system automatically saves:
- **Current workflow stage** (1-11)
- **Last action** ("next" or "back")
- **Timestamp** (when workflow was updated)
- **Workflow history** (last 10 stage transitions)

### 2. Automatic State Restoration

On server restart or session resume:
- State is restored from persistent session storage (ADK DatabaseSessionService)
- Workflow continues from the last saved stage
- History is preserved for reference

### 3. Integration Points

**During Session Startup:**
```python
# In artifact_manager.py::rehydrate_session_state()
rehydrate_session_state(state)  # Restores workflow state automatically
```

**During Workflow Navigation:**
```python
# In ds_tools.py::next_stage() / back_stage()
from .workflow_persistence import save_workflow_state
save_workflow_state(state, stage_id, action)  # Saves to persistent storage
```

## State Structure

```python
state = {
    "workflow_stage": 5,  # Current stage (1-11)
    "last_workflow_action": "next",  # "next" or "back"
    "workflow_started_at": "2025-01-28T10:30:00",
    "workflow_updated_at": "2025-01-28T11:45:00",
    "workflow_history": [
        {"stage_id": 1, "action": "initialized", "timestamp": "..."},
        {"stage_id": 2, "action": "next", "timestamp": "..."},
        {"stage_id": 3, "action": "next", "timestamp": "..."},
        # ... last 10 transitions
    ]
}
```

## Persistence Backend

### DatabaseSessionService (Recommended)

If using `DatabaseSessionService`:
- ✅ State persists automatically in SQLite database
- ✅ Survives server restarts
- ✅ Available across sessions for same user
- ✅ Full audit trail

**Location:** `data_science/db/adk.sqlite3`

### InMemorySessionService

If using `InMemorySessionService`:
- ⚠️ State only persists during session
- ⚠️ Lost on server restart
- ✅ Still works for same-session navigation

**Recommendation:** Switch to `DatabaseSessionService` for production use.

## Example Workflow

### Scenario: Long-Running Analysis

**Before Server Restart:**
```
1. Upload data.csv
2. next_stage() → Stage 1 (Collection)
3. next_stage() → Stage 2 (Cleaning)
4. next_stage() → Stage 3 (EDA)
5. describe() - Analyze statistics
6. next_stage() → Stage 4 (Visualization)
7. [Server restarts...]
```

**After Server Restart:**
```
✅ Workflow state restored from database
✅ Current stage: 4 (Visualization)
✅ Continue with visualization tools
8. plot() - Generate visualizations
9. next_stage() → Stage 5 (Feature Engineering)
```

## API Reference

### `save_workflow_state(state, stage_id, action)`

Save workflow state to session.

**Parameters:**
- `state`: Session state dictionary
- `stage_id`: Current workflow stage (1-11)
- `action`: Last action ("next" or "back")

### `restore_workflow_state(state)`

Restore workflow state from session.

**Parameters:**
- `state`: Session state dictionary

**Returns:**
- `int`: Current workflow stage (1-11) or `None` if not found

### `get_workflow_info(state)`

Get comprehensive workflow information.

**Parameters:**
- `state`: Session state dictionary

**Returns:**
- `dict`: Workflow info with stage, history, next/prev stages, etc.

## Implementation Details

### File: `workflow_persistence.py`

New module providing:
- `save_workflow_state()` - Save workflow state
- `restore_workflow_state()` - Restore workflow state
- `get_workflow_info()` - Get workflow information

### File: `artifact_manager.py`

**Updated:** `rehydrate_session_state()`
- Now restores workflow state on session startup
- Logs restoration for debugging

### File: `ds_tools.py`

**Updated:** `next_stage()` and `back_stage()`
- Automatically save workflow state using persistence module
- Restore state before navigation
- Fallback to direct state update if persistence unavailable

## Benefits

1. ✅ **Resume Workflow** - Continue from last stage after restart
2. ✅ **Workflow History** - Track last 10 stage transitions
3. ✅ **Metadata** - Timestamps for workflow start/update
4. ✅ **Seamless Integration** - Works with existing ADK session services
5. ✅ **Backward Compatible** - Falls back gracefully if persistence unavailable

## Troubleshooting

### Workflow Starts at Stage 1 After Restart

**Possible Causes:**
1. Using `InMemorySessionService` instead of `DatabaseSessionService`
2. Session not properly persisted
3. Database permissions issue

**Solution:**
- Verify `DatabaseSessionService` is being used
- Check database file exists: `data_science/db/adk.sqlite3`
- Review logs for workflow restoration messages

### Workflow State Not Updating

**Possible Causes:**
1. State not being saved (persistence module unavailable)
2. Database write permissions

**Solution:**
- Check logs for `[WORKFLOW] ✅ Saved workflow state` messages
- Verify database is writable
- Check fallback to direct state update is working

## Best Practices

1. **Use DatabaseSessionService** for production deployments
2. **Monitor workflow logs** to verify persistence is working
3. **Check state on session start** to confirm restoration
4. **Use workflow history** to understand user journey

---

**Status:** ✅ Production Ready

**Version:** 1.0

**Last Updated:** 2025-01-28

