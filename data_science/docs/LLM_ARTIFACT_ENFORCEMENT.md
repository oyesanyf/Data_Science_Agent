# LLM-Enforced Artifact Creation System

## Overview

An intelligent artifact creation system that uses LLM to:
1. **Analyze tool results** and determine required artifacts
2. **Enforce artifact creation** ensuring all artifacts are:
   - Saved to UI (via ADK artifact service)
   - Saved as MD files with results
   - Saved to filesystem
3. **Validate compliance** using LLM to check artifact quality

## ADK Artifact Service Integration

This system follows the **official ADK artifact service pattern** from [Chapter 18 - Artifact Management](https://amulyabhatia.com/building-intelligent-agents-with-google-adk/chapter-18-artifact-management):

- Uses `tool_context.save_artifact(filename, artifact_part)` where `artifact_part` is a `google.genai.types.Part`
- For text files (markdown, JSON): `Part(text=file_content)`
- For binary files (images, PDFs): `Part(inline_data=Blob(mime_type=mime_type, data=file_bytes))`
- Artifacts are automatically available via `LoadArtifactsTool` for LLM awareness
- Artifacts appear in the UI artifacts panel

## How It Works

### Step 1: LLM Analysis
The LLM analyzes the tool result and determines what artifacts are required:

```python
llm_validate_artifact_requirements(tool_name, result)
```

**LLM Prompt:**
```
Analyze this tool execution result and determine what artifacts must be created:
- Markdown summary (MD file with formatted results)
- File artifacts (if result contains model_path, plot_path, etc.)
- JSON summary (for LLM accessibility)

Return JSON with required artifacts and validation checks.
```

**LLM Response:**
```json
{
    "required_artifacts": [
        {
            "type": "markdown",
            "filename": "train_classifier_output.md",
            "description": "Markdown summary of tool execution",
            "required": true
        },
        {
            "type": "file",
            "filename": "model.joblib",
            "source_path": "model_path from result",
            "required": true
        },
        {
            "type": "json_summary",
            "filename": "train_classifier_summary.json",
            "required": true
        }
    ],
    "validation_checks": [
        "artifact_must_be_saved_to_ui",
        "artifact_must_be_saved_to_filesystem",
        "artifact_must_be_markdown_with_results"
    ]
}
```

### Step 2: Artifact Enforcement
Based on LLM requirements, the system creates all required artifacts:

```python
llm_enforce_artifact_creation(tool_name, result, tool_context)
```

**Actions:**
1. Creates markdown artifact with full results → `workspace/reports/{tool_name}_output.md`
2. Saves file artifacts (from result) → `workspace/models/`, `workspace/plots/`, etc.
3. Creates JSON summary → `workspace/reports/{tool_name}_summary.json`
4. Saves all artifacts to UI via `tool_context.save_artifact()`
5. Saves all artifacts to filesystem

### Step 3: LLM Validation
After creation, LLM validates compliance:

```python
_llm_validate_artifacts(...)
```

**Validation Checks:**
- ✅ `artifact_must_be_saved_to_ui` - All artifacts saved via ADK service?
- ✅ `artifact_must_be_saved_to_filesystem` - All artifacts saved to disk?
- ✅ `artifact_must_be_markdown_with_results` - Markdown contains results?

**LLM Recommendations:**
If validation fails, LLM provides specific recommendations:
```json
{
    "compliance": {
        "saved_to_ui": true,
        "saved_to_filesystem": true,
        "has_markdown": true
    },
    "issues": [],
    "recommendations": []
}
```

## Integration

### Automatic Enforcement
The system is automatically called for ALL tools via `_ensure_ui_display()`:

```python
# In adk_safe_wrappers.py
_ensure_artifacts_created(result, tool_name, tool_context)
    ↓
llm_enforce_artifact_creation(result, tool_name, tool_context)
    ↓
1. LLM determines requirements
2. Creates all artifacts
3. Saves to UI + filesystem
4. Validates compliance
```

### Configuration
Enable/disable LLM enforcement via environment variable:

```bash
# Enable (default)
USE_LLM_ARTIFACT_ENFORCEMENT=1

# Disable (fallback to regular artifact creation)
USE_LLM_ARTIFACT_ENFORCEMENT=0
```

## Artifact Types Created

### 1. Markdown Artifacts
**File:** `{tool_name}_output.md`  
**Location:** `workspace/reports/`  
**Content:** (ALWAYS includes results)
- Tool name and timestamp
- Status with emoji indicator
- **Results section** (ALWAYS populated with actual tool output):
  - Priority 1: Pre-formatted `__display__` text (best quality)
  - Priority 2: Structured data (`overview`, `data`, `summary`, `insights`)
  - Priority 3: All non-metadata fields from result dict
  - Fallback: Status message with available keys
- Metrics (if available)
- Data summary (shape, columns, missing values)
- List of generated artifacts

**Guarantees:**
- ✅ **Results ALWAYS included** - Never creates empty markdown files
- ✅ Multi-source extraction - Pulls from 7+ possible fields
- ✅ Content validation - Checks file size and content quality before saving
- ✅ Fallback protection - Even if tool fails, markdown shows what happened

**Saved:**
- ✅ To filesystem: `workspace/reports/{tool_name}_output.md`
- ✅ To UI: Via ADK artifact service using `tool_context.save_artifact(filename, Part(text=markdown_content))`
  - Creates `types.Part(text=markdown_content)` for text-based files
  - Proper MIME type: `text/markdown`
  - Available via `LoadArtifactsTool` for LLM awareness

### 2. File Artifacts
**File:** Original filename (e.g., `model.pkl`, `plot.png`)  
**Location:** `workspace/models/`, `workspace/plots/`, etc.  
**Auto-categorized by extension:**
- `.pkl`, `.joblib` → `models/`
- `.png`, `.jpg` → `plots/`
- `.pdf`, `.html` → `reports/`
- Others → `data/`

**Saved:**
- ✅ To filesystem: Organized in workspace subdirectories
- ✅ To UI: Via `tool_context.save_artifact()`

### 3. JSON Summary Artifacts
**File:** `{tool_name}_summary.json`  
**Location:** `workspace/reports/`  
**Content:**
```json
{
    "tool": "train_classifier",
    "status": "success",
    "timestamp": "2025-01-28T...",
    "summary": "Tool execution message",
    "metrics": {"accuracy": 0.95, ...},
    "overview": {...},
    "shape": [1000, 10],
    "columns": ["col1", "col2", ...],
    "artifacts": ["model.joblib", "train_classifier_output.md"],
    "artifact_placeholders": {
        "{artifact.train_classifier_summary.json}": "Content of summary"
    }
}
```

**Purpose:**
- LLM accessibility via `{artifact.{tool_name}_summary.json}` placeholder
- Quick reference for tool execution results
- Cross-tool data sharing

**Saved:**
- ✅ To filesystem: `workspace/reports/{tool_name}_summary.json`
- ✅ To UI: Via ADK artifact service using `tool_context.save_artifact(filename, Part(text=json_content))`
  - Creates `types.Part(text=json_content)` for JSON files
  - Proper MIME type: `application/json`
  - Enables `{artifact.{tool_name}_summary.json}` placeholder usage

## Example Workflow

### Tool Execution: `train_classifier()`

**1. Tool Returns:**
```python
{
    "status": "success",
    "model_path": "model.joblib",
    "metrics": {"accuracy": 0.95},
    "message": "Model trained successfully"
}
```

**2. LLM Analysis:**
```json
{
    "required_artifacts": [
        {"type": "markdown", "filename": "train_classifier_output.md"},
        {"type": "file", "source_path": "model.joblib"},
        {"type": "json_summary", "filename": "train_classifier_summary.json"}
    ]
}
```

**3. Artifact Creation:**
- ✅ `workspace/reports/train_classifier_output.md` (with full results)
- ✅ `workspace/models/model.joblib` (copied from original)
- ✅ `workspace/reports/train_classifier_summary.json` (for LLM access)

**4. Save to UI:**
- ✅ All 3 artifacts saved via `tool_context.save_artifact()`
- ✅ Available in ADK UI artifacts panel

**5. Validation:**
- ✅ All artifacts saved to UI? YES
- ✅ All artifacts saved to filesystem? YES
- ✅ Markdown contains results? YES

## Fixing "describe had no results" Issue

**Problem:** Tools like `describe()` were showing `result: null` in the ADK UI even though they executed successfully.

**Root Cause:** ADK's artifact service requires artifacts to be saved via `tool_context.save_artifact()` using `types.Part` objects. Simply returning dict results with `__display__` wasn't enough - artifacts must be explicitly saved to the artifact service.

**Solution:** This LLM-enforced system ensures:
1. ✅ All tool results are saved as markdown artifacts via ADK artifact service
2. ✅ Artifacts are created as `types.Part` objects (text or binary)
3. ✅ Artifacts appear in the UI artifacts panel
4. ✅ `__display__` field is always populated for direct UI display
5. ✅ Artifacts are available via `LoadArtifactsTool` for LLM awareness

**Result:** Tools like `describe()` now:
- Display results in chat (via `__display__` field)
- Save markdown artifacts to UI (via `save_artifact()`)
- Make artifacts available for subsequent LLM queries
- Persist results to filesystem for session persistence

## Benefits

1. **LLM Intelligence**: Determines what artifacts are needed based on tool result
2. **Automatic Enforcement**: Creates all required artifacts automatically
3. **Validation**: LLM validates compliance with ADK best practices
4. **Dual Storage**: Saves to both filesystem and UI
5. **LLM Accessibility**: JSON summaries enable `{artifact.filename}` placeholders
6. **Fail-Safe**: Falls back to regular artifact creation if LLM unavailable
7. **ADK Compliance**: Follows official ADK artifact service patterns
8. **UI Visibility**: Ensures all results appear in ADK UI via artifacts + display fields
9. **Results Guarantee**: **MD files ALWAYS contain actual results** - never empty placeholders
10. **Multi-Source Extraction**: Aggressively extracts from 7+ possible fields to ensure results are included

## LLM Fallback

If LLM is unavailable (no API key, network error, etc.):
- Falls back to regular `universal_artifact_creator`
- Still creates artifacts, just without LLM intelligence
- System continues to work normally

## Environment Variables

```bash
# Enable/disable LLM enforcement (default: enabled)
USE_LLM_ARTIFACT_ENFORCEMENT=1

# LLM model for artifact analysis (default: gpt-4o-mini)
LLM_ARTIFACT_MODEL=gpt-4o-mini
```

## Result Enhancement

Tool results are enhanced with artifact information:

```python
result["llm_artifact_enforcement"] = {
    "required_count": 3,
    "created_count": 3,
    "failed_count": 0,
    "validation": {
        "compliance": {
            "saved_to_ui": true,
            "saved_to_filesystem": true,
            "has_markdown": true
        },
        "issues": [],
        "recommendations": []
    },
    "artifacts_created": [
        {"type": "markdown", "filename": "train_classifier_output.md", ...},
        {"type": "file", "filename": "model.joblib", ...},
        {"type": "json_summary", "filename": "train_classifier_summary.json", ...}
    ]
}

result["artifact_placeholders"] = {
    "{artifact.train_classifier_output.md}": "Content of train_classifier_output.md",
    "{artifact.model.joblib}": "Content of model.joblib",
    "{artifact.train_classifier_summary.json}": "Content of train_classifier_summary.json"
}
```

This allows LLM agents to reference artifacts using placeholders in prompts!

