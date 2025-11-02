# Auto-Correction System

## Overview

The Data Science Agent includes a comprehensive **auto-correction system** that automatically fixes common issues as they occur during tool execution. This system ensures tools continue to work even when errors occur, providing a seamless user experience.

## Features

### 1. **Artifact Auto-Correction**
- **Missing directories**: Automatically creates missing artifact workspace directories
- **Missing display fields**: Adds `__display__`, `message`, `ui_text` if missing
- **Non-dict results**: Converts results to proper dictionary format
- **JSON serialization**: Fixes non-serializable values in results

### 2. **Workflow State Auto-Correction**
- **Missing workflow state**: Restores from persistent storage or initializes defaults
- **Invalid stage values**: Corrects stage numbers out of range (1-11)
- **Corrupted history**: Fixes corrupted workflow history arrays
- **State synchronization**: Ensures workflow state is consistent

### 3. **Import/Auto-Install Auto-Correction**
- **Missing dependencies**: Automatically installs missing packages
- **Tool-specific installs**: Uses tool dependency mapping for precise installs
- **Retry after install**: Automatically retries tool execution after successful install
- **Fallback strategies**: Tries multiple approaches if first attempt fails

### 4. **Generic Error Auto-Correction**
- **Missing results**: Creates default success result if None
- **Missing status fields**: Adds required status field
- **Error type detection**: Identifies error category and applies appropriate fix
- **Nested error detection**: Finds ImportErrors buried in other exceptions

## How It Works

### Error Handling Flow

```
Tool Execution
    ↓
Exception Occurs
    ↓
Auto-Correction System Activated
    ↓
┌─────────────────────────────────┐
│  1. Detect Error Type          │
│     - ImportError               │
│     - Artifact Error            │
│     - Workflow Error            │
│     - Generic Error             │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  2. Apply Auto-Correction       │
│     - Fix artifact issues       │
│     - Fix workflow state        │
│     - Auto-install packages     │
│     - Fix result structure      │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  3. Retry Tool Execution        │
│     (after successful fix)      │
└─────────────────────────────────┘
    ↓
    ├─ Success → Return Result
    └─ Failure → Return Helpful Error Message
```

### Implementation in `safe_tool_wrapper`

The auto-correction system is integrated into `safe_tool_wrapper` in `agent.py`:

1. **Catches ImportError**: Attempts auto-correction, then auto-install, then retry
2. **Catches all exceptions**: Tries auto-correction before returning error
3. **Artifact generation**: Wraps artifact creation in auto-correction
4. **Never breaks**: All correction attempts are wrapped in try/except

## Auto-Correction Functions

### `auto_correct_artifact_error(tool_name, error, tool_context, result)`

Fixes artifact-related issues:
- Creates missing directories
- Adds display fields
- Converts non-dict results
- Fixes JSON serialization

### `auto_correct_workflow_error(tool_name, error, tool_context)`

Fixes workflow state issues:
- Restores missing state from persistence
- Initializes default state
- Fixes invalid stage numbers
- Cleans corrupted history

### `auto_correct_import_error(tool_name, error, tool_context)`

Fixes import/installation issues:
- Extracts missing module name
- Uses tool dependency mapping
- Installs packages automatically
- Returns success/failure status

### `auto_correct_common_errors(tool_name, error, tool_context, result)`

Comprehensive error correction:
- Routes to appropriate correction function
- Handles multiple error types
- Creates fallback results
- Never raises exceptions

## Safety Features

### 1. **Never Raises Exceptions**
All auto-correction functions are wrapped in try/except blocks and never raise exceptions. They return status tuples indicating success/failure.

### 2. **Graceful Degradation**
If auto-correction fails, the system returns helpful error messages instead of crashing.

### 3. **Logging**
All correction attempts are logged at appropriate levels:
- `INFO`: Successful corrections
- `WARNING`: Correction failures (non-critical)
- `DEBUG`: Correction system errors (for debugging)

### 4. **Retry Logic**
After successful correction, tools are automatically retried once before giving up.

## Examples

### Example 1: Missing Artifact Directory

```python
# Tool tries to save artifact
# Error: "No such file or directory: 'workspace/artifacts/'"
# Auto-correction: Creates workspace directory
# Result: Tool succeeds after retry
```

### Example 2: Missing Package

```python
# Tool imports featuretools
# Error: "No module named 'featuretools'"
# Auto-correction: Installs featuretools
# Result: Tool succeeds after retry with installed package
```

### Example 3: Corrupted Workflow State

```python
# Tool reads workflow_stage
# Error: "KeyError: 'workflow_stage'"
# Auto-correction: Restores from persistence or initializes to 1
# Result: Tool succeeds with corrected state
```

### Example 4: Missing Display Fields

```python
# Tool returns result without __display__
# Auto-correction: Extracts from message/ui_text and adds all display fields
# Result: Result is properly formatted for UI display
```

## Benefits

1. **Zero Manual Intervention**: Users don't need to manually fix issues
2. **Seamless Experience**: Tools "just work" even when errors occur
3. **Self-Healing**: System fixes itself automatically
4. **Comprehensive Coverage**: Handles artifacts, workflow, and dependencies
5. **Safe**: Never crashes - always returns a valid response

## Future Enhancements

- Add more specific error patterns
- Expand correction strategies
- Add user preference for auto-correction
- Add correction history/audit trail
- Add metrics on correction success rates

