# Architecture Documentation

## System Overview

The Data Science Agent is built on Google's Agent Development Kit (ADK) with a layered architecture designed for scalability, maintainability, and production readiness.

## Architecture Layers

```
┌─────────────────────────────────────────┐
│           UI (Chat Interface)            │
├─────────────────────────────────────────┤
│         ADK Runner & Agent Core          │
├─────────────────────────────────────────┤
│    Callbacks & Guards (Middleware)       │
├─────────────────────────────────────────┤
│        Tool Routers & Registry           │
├─────────────────────────────────────────┤
│       ADK-Safe Wrappers Layer            │
├─────────────────────────────────────────┤
│      Core DS Tools (150+ functions)      │
├─────────────────────────────────────────┤
│    Artifact & Workspace Management       │
├─────────────────────────────────────────┤
│         Storage & File System            │
└─────────────────────────────────────────┘
```

## Core Components

### 1. Agent Core (`agent.py`)

**Purpose**: Main agent definition and orchestration

**Key Responsibilities**:
- Agent initialization with LLM configuration
- Tool registration and lifecycle management
- Callback registration (before/after tool execution)
- Circuit breaker pattern for LLM failover
- File upload handling

**Design Patterns**:
- **Circuit Breaker**: Automatic failover from Gemini to OpenAI
- **Middleware Pattern**: Before/after callbacks for cross-cutting concerns
- **Safe Tool Wrapper**: Error recovery for all tool executions

### 2. Tool Layer

#### ADK-Safe Wrappers (`adk_safe_wrappers.py`)

**Purpose**: Compatibility layer between ADK and core tools

**Key Features**:
- JSON-serializable parameters only
- `tool_context` extraction from kwargs
- Consistent error handling
- Type conversions (JSON strings → Python objects)

**Example**:
```python
def grid_search_tool(
    target: str, 
    model: str, 
    param_grid: str = "{}",  # JSON string
    csv_path: str = "", 
    **kwargs
) -> Dict[str, Any]:
    tool_context = kwargs.get("tool_context")
    param_dict = json.loads(param_grid)  # Convert to dict
    return grid_search(
        target=target,
        model=model,
        param_grid=param_dict,
        csv_path=csv_path,
        tool_context=tool_context
    )
```

#### Core DS Tools (`ds_tools.py`)

**Purpose**: Actual data science implementations

**Key Features**:
- Native Python types
- Async support where beneficial
- Direct access to tool_context
- Rich return types (dict with artifacts, plots, etc.)

### 3. Routing Layer

#### Generic Router (`routers.py`)

**Purpose**: Intelligent action dispatching

**Flow**:
```python
route_user_intent_tool(action, params)
  ├─> Plot aliases → plot_tool (direct)
  ├─> Analysis actions → auto_analysis_guard
  ├─> Unstructured actions → unstructured tools
  └─> Other → TOOL_REGISTRY lookup
```

**Hard-routed Actions**:
- `plot`, `visualize`, `charts` → `plot_tool`
- `analyze`, `eda` → `auto_analysis_guard`
- `unstructured`, `list_unstructured` → unstructured tools

#### ✅ Streaming Router (ENABLED)

**Purpose**: Multiplex streaming tools under single endpoint for real-time progress updates

**Supported Streams** (15+ tools):
- Full EDA pipeline with real-time updates
- Data cleaning + validation workflows
- Feature engineering pipeline
- Model training with progress tracking
- Hyperparameter optimization (trial-by-trial)
- Evaluation + SHAP explanations
- Batch inference with progress bars
- Deep learning training (per-batch loss)
- Prophet time series forecasting (phase-by-phase)
- Drift monitoring with real-time alerts
- Fairness analysis + governance tracking
- Causal inference workflows
- Executive report generation with progress

### 4. Guard Layer

Hardened wrappers that ensure robustness:

#### Plot Tool Guard (`plot_tool_guard.py`)

**Guarantees**:
1. Workspace exists before plotting
2. Files are created (with fallback generation)
3. Artifacts registered in system
4. Files pushed to UI
5. Friendly chat message returned

**Fallback Strategy**:
```python
if no plots created:
    generate_fallback_plots()  # 3 EDA plots
    register_all_artifacts()
    push_to_ui()
```

#### Executive Report Guard (`executive_report_guard.py`)

**Guarantees**:
1. PDF is written to workspace/reports/
2. File registered as artifact
3. File pushed to UI
4. Concise chat summary

#### Head/Describe Guards (`head_describe_guard.py`)

**Guarantees**:
1. Data preview/summary generated
2. Results shown in chat
3. Any artifacts pushed to UI

### 5. Callback System

#### Before Model Callback (`_handle_file_uploads_callback`)

**Purpose**: Process file uploads before LLM sees them

**Flow**:
```
User uploads CSV
  → Stream to disk (no memory spike)
  → Create workspace
  → Register artifact
  → Convert to text reference
  → Set default_csv_path in state
  → Mirror to UI
```

**LiteLLM Compatibility**:
- Only `image/*`, `video/*`, `application/pdf` as inline_data
- CSV → text summary with file_id
- Unsupported types → text references

#### After Tool Callback (`after_tool_callback`)

**Purpose**: Post-process tool results

**Responsibilities**:
1. **Result Sanitization**: Ensure JSON-serializable
2. **State Management**: Store canonical state (last_model, last_metrics)
3. **Ghost Success Blocking**: Fail if plot tool reports success but no artifacts
4. **Chat Promotion**: Promote `ui_text` to chat message
5. **Belt-and-Suspenders**: Auto-push any returned artifacts

### 6. Workspace Management

#### Artifact Manager (`artifact_manager.py`)

**Purpose**: Organize files per dataset

**Workspace Creation**:
```python
ensure_workspace(state, upload_root)
  → Create: {WORKSPACES_ROOT}/{dataset_slug}/{run_id}/
    ├─ uploads/
    ├─ plots/
    ├─ models/
    ├─ reports/
    ├─ data/
    ├─ metrics/
    ├─ indexes/
    ├─ logs/
    ├─ tmp/
    ├─ manifests/
    └─ unstructured/  # NEW
```

**Artifact Registration**:
```python
register_artifact(state, file_path, kind, label)
  → Track in _ARTIFACTS registry
  → Version management
  → Latest-by-label tracking
```

**Artifact Routing**:
- Decorator pattern: `@make_artifact_routing_wrapper`
- Automatic copy/move from temp locations to workspace
- Tool result inspection for `plots`, `artifacts` keys

#### Artifact Utils (`artifact_utils.py`)

**Purpose**: Helper functions for artifact handling

**Key Functions**:
- `guess_mime(path)` - MIME type detection
- `_exists(path)` - Safe file existence check
- `push_artifact_to_ui(context, path, name)` - Async UI push
- `sync_push_artifact(...)` - Sync wrapper for async push

**Debouncing**:
```python
_uploaded_once: set[(name, size, mtime)]
# Prevents duplicate uploads within same run
```

### 7. Unstructured Data System

**Components**:
- `unstructured_handler.py` - Processing logic
- `unstructured_tools.py` - ADK wrappers
- Workspace integration - `.unstructured/` folder

**Supported Types**:
- PDFs (text extraction, page counting)
- Images (dimension analysis)
- Text files (word/line counting)

**Flow**:
```
Upload PDF
  → process_unstructured_file()
  → Copy to workspace/unstructured/
  → Register as artifact (kind="unstructured")
  → Push to UI
  → Return summary
```

## Data Flow

### Typical Analysis Session

```
1. User uploads CSV
   ├─> _handle_file_uploads_callback()
   │   ├─> save_upload() streams to disk
   │   ├─> derive_dataset_slug() from filename
   │   ├─> ensure_workspace() creates structure
   │   ├─> register_artifact(kind="upload")
   │   └─> set default_csv_path in state

2. User: "analyze my data"
   ├─> route_user_intent_tool(action="analyze")
   │   └─> auto_analysis_guard()
   │       ├─> analyze_dataset_tool()
   │       ├─> head_tool_guard()
   │       └─> describe_tool_guard()
   ├─> after_tool_callback()
   │   ├─> Sanitize results
   │   ├─> Store state (last_model, etc.)
   │   ├─> Promote ui_text to chat
   │   └─> Auto-push artifacts

3. User: "plot the data"
   ├─> route_user_intent_tool(action="plot")
   │   └─> plot_tool_guard()
   │       ├─> ensure_workspace()
   │       ├─> plot_tool() generates PNGs
   │       ├─> (fallback if no plots created)
   │       ├─> register_artifact(kind="plot")
   │       └─> push_artifact_to_ui()
   ├─> after_tool_callback()
   │   └─> Promote message to chat

4. User: "create executive report"
   ├─> route_user_intent_tool(action="export_executive_report")
   │   └─> export_executive_report_tool_guard()
   │       ├─> ensure_workspace()
   │       ├─> export_executive_report() generates PDF
   │       ├─> register_artifact(kind="report")
   │       └─> push_artifact_to_ui()
```

## Error Handling Strategy

### Layers of Protection

1. **Tool-level try-catch**: Each tool returns `{"error": "...", "status": "failed"}`
2. **Safe Tool Wrapper**: Catches all exceptions, ensures response
3. **Callback try-catch**: Never crash callback (would corrupt sequences)
4. **Circuit Breaker**: LLM failover (Gemini → OpenAI)
5. **Guard fallbacks**: Generate placeholder artifacts if tool fails

### Result Sanitization

```python
def _safe(obj):
    """Ensure JSON-serializable"""
    if is_generator(obj):
        return "[non-serializable: generator]"
    try:
        return json.loads(json.dumps(obj, default=str))
    except:
        return str(obj)
```

Applied to:
- All `callback_context.state` values
- Tool return values
- Cache plugin storage

## Session State Management

### Key State Variables

```python
state = {
    # File & Dataset
    "default_csv_path": "/path/to/file.csv",
    "force_default_csv": True,
    "original_dataset_name": "tips",
    "last_file_id": "1761019819_uploaded.csv",
    
    # Workspace
    "workspace_root": "/path/to/workspace/tips/20251021_120000",
    "workspace_run_id": "20251021_120000",
    "workspace_paths": {
        "uploads": "/path/...",
        "plots": "/path/...",
        # ... all subdirs
    },
    
    # Model & Metrics
    "last_model": "random_forest",
    "last_metrics": {"accuracy": 0.95, ...},
    "last_predictions": [...],
    
    # Artifacts
    "mirrored_upload_saved": True,
}
```

### State Lifecycle

1. **Upload**: Set `default_csv_path`, create workspace
2. **Analysis**: Update `last_model`, `last_metrics`
3. **Training**: Store model info
4. **Prediction**: Store predictions
5. **Report**: All info available for summary

## Performance Considerations

### Memory Management
- **Streaming uploads**: No in-memory file storage
- **Lazy imports**: Deep learning tools imported on demand
- **Parquet auto-conversion**: Smaller footprint than CSV

### Caching
- **Tool result cache**: Avoid re-running expensive operations
- **LLM response cache**: Reduce API costs
- **Artifact deduplication**: Track by (name, size, mtime)

### Concurrency
- **Async tools**: Non-blocking I/O for file operations
- **Background tasks**: Artifact uploads don't block responses
- **Thread-safe**: File uploads use locks

## Security Considerations

### File Upload Safety
- **Sanitized filenames**: Remove special characters
- **Length limits**: Prevent path traversal
- **MIME validation**: Only allowed types
- **Streaming**: Prevents DoS via large files

### Path Security
- **No absolute paths in UI**: Use file_id references
- **Workspace isolation**: Per-dataset directories
- **Resolve file_id**: Secure path resolution

### API Key Management
- **Environment variables**: Never hardcoded
- **Fallback logic**: Graceful degradation
- **Circuit breaker**: Automatic rate limit handling

## Deployment

### Production Checklist

- [ ] Set `SESSION_SERVICE_URI` for persistent sessions
- [ ] Configure `WORKSPACES_ROOT` for shared storage
- [ ] Set `LOG_LEVEL=INFO` (not DEBUG)
- [ ] Enable `LITELLM_MAX_RETRIES`
- [ ] Set reasonable `LITELLM_TIMEOUT_SECONDS`
- [ ] Configure backup strategy for workspaces
- [ ] Set up log rotation
- [ ] Monitor artifact storage growth

### Scaling Considerations

**Horizontal Scaling**:
- Share `WORKSPACES_ROOT` via NFS/S3
- Use external session service (Redis/MongoDB)
- Load balance at reverse proxy level

**Vertical Scaling**:
- Increase worker count
- Add GPU support for deep learning
- Increase file upload size limits

## Testing Strategy

### Unit Tests
- Tool wrappers (input/output validation)
- Artifact management (workspace creation, registration)
- Routers (action dispatching)

### Integration Tests
- End-to-end workflows (upload → analyze → plot → report)
- Callback chains (before → tool → after)
- Error scenarios (network failures, file errors)

### Smoke Tests
```bash
1. Upload CSV → verify workspace created
2. Run analyze → verify artifacts generated
3. Run plot → verify PNGs in workspace + UI
4. Run report → verify PDF in workspace + UI
```

---

**Last Updated**: 2025-10-21
**Version**: 1.0.0

