# LLM-Guided Dataset Workspace Management

## Overview

A comprehensive system that allows the LLM to intelligently create, organize, and manage directory structures for datasets. Files are automatically organized by type (models, plots, data, reports, etc.) based on dataset names.

## Key Features

1. **LLM-Guided Dataset Naming**: Uses LLM to suggest descriptive dataset names from file headers and data
2. **Automatic Directory Structure**: Creates organized subdirectories for different file types
3. **Intelligent File Organization**: Automatically categorizes and saves files to appropriate locations
4. **Workspace Discovery**: List and query workspace information by dataset name

## Directory Structure

Each dataset gets its own workspace with the following structure:

```
uploads/_workspaces/{dataset_name}/
  ├─ data/          # Processed datasets (CSV, Parquet, Feather)
  ├─ models/        # Trained ML models (.pkl, .joblib, .onnx)
  ├─ plots/         # Visualizations (PNG, SVG, PDF)
  ├─ reports/       # Analysis reports (PDF, HTML, MD)
  ├─ metrics/       # Evaluation metrics (JSON, CSV)
  ├─ feature_sets/  # Engineered features
  ├─ embeddings/    # Vector embeddings and indexes
  ├─ logs/         # Execution logs
  ├─ cache/        # Cache files
  ├─ notebooks/    # Jupyter notebooks and scripts
  ├─ config/       # Configuration files
  ├─ backups/      # Backup copies
  └─ manifest.json # Workspace metadata
```

## Available Tools

### 1. `create_dataset_workspace_tool`

Creates or ensures a workspace exists for a dataset.

**Parameters:**
- `dataset_name` (optional): Explicit dataset name
- `file_path` (optional): Path to dataset file
- `headers` (optional): Comma-separated column headers
- `context` (optional): Additional context about the dataset

**Example:**
```
create_dataset_workspace_tool(
    file_path="customer_data.csv",
    headers="customer_id,age,income,education",
    context="Customer demographics dataset"
)
```

**What it does:**
- Derives intelligent dataset name using LLM (if enabled) or file-based heuristics
- Creates comprehensive directory structure
- Generates manifest.json with metadata

### 2. `save_file_to_workspace_tool`

Automatically saves files to the appropriate workspace location based on file type.

**Parameters:**
- `file_path`: Source file to save
- `dataset_name`: Dataset workspace name
- `destination_name` (optional): Custom destination filename
- `file_type` (optional): Explicit type override ("data", "model", "plot", etc.)

**Example:**
```
save_file_to_workspace_tool(
    file_path="trained_model.pkl",
    dataset_name="customer_analysis",
    file_type="model"
)
```

**File Type Detection:**
- `.pkl`, `.joblib`, `.onnx` → `models/`
- `.png`, `.svg`, `.pdf` → `plots/`
- `.csv`, `.parquet` → `data/`
- `.json`, `.yaml` → `metrics/`
- `.html`, `.md`, `.pdf` → `reports/`
- And more...

### 3. `list_workspace_files_tool`

Lists all files in a workspace, optionally filtered by type.

**Parameters:**
- `dataset_name`: Dataset workspace name
- `file_type` (optional): Filter by type ("data", "model", "plot", etc.)

**Example:**
```
list_workspace_files_tool(
    dataset_name="customer_analysis",
    file_type="plots"
)
```

**Returns:**
- List of files with metadata (name, path, type, size, modified date)
- Files grouped by type
- Summary counts per type

### 4. `get_workspace_info_tool_v2`

Gets detailed information about a workspace.

**Parameters:**
- `dataset_name`: Dataset workspace name

**Example:**
```
get_workspace_info_tool_v2(
    dataset_name="customer_analysis"
)
```

**Returns:**
- Workspace root path
- All subdirectory paths
- Creation timestamp
- File counts per directory

## LLM Dataset Naming

The system can use LLM to suggest intelligent dataset names based on:
- Column headers
- Sample data
- File path
- Additional context

**Enable LLM Naming:**
Set environment variable: `ENABLE_LLM_DATASET_NAMING=1`

**Naming Priority:**
1. LLM suggestion (if enabled and headers provided)
2. File basename (sanitized)
3. Headers-based name
4. Fallback to "dataset"

## Usage Workflow

### Step 1: Create Workspace
```
create_dataset_workspace_tool(
    file_path="uploads/sales_data.csv",
    headers="date,sales,region,customer_id"
)
```

### Step 2: Save Generated Files
```
# Save a trained model
save_file_to_workspace_tool(
    file_path="model.pkl",
    dataset_name="sales_data",
    file_type="model"
)

# Save a plot (auto-detected)
save_file_to_workspace_tool(
    file_path="correlation_heatmap.png",
    dataset_name="sales_data"
)

# Save cleaned data
save_file_to_workspace_tool(
    file_path="cleaned_data.csv",
    dataset_name="sales_data",
    file_type="data"
)
```

### Step 3: List Files
```
list_workspace_files_tool(
    dataset_name="sales_data"
)
```

### Step 4: Get Workspace Info
```
get_workspace_info_tool_v2(
    dataset_name="sales_data"
)
```

## Integration with Existing System

The workspace manager integrates seamlessly with the existing artifact_manager system:

- **Compatible**: Works alongside existing workspace structures
- **Non-invasive**: Doesn't conflict with existing file organization
- **Extensible**: Can be used independently or with existing tools

## Benefits

1. **Organization**: Clear separation of file types per dataset
2. **Traceability**: Manifest files track workspace creation and structure
3. **Discoverability**: Easy to find files by dataset name and type
4. **Scalability**: Each dataset has isolated workspace
5. **LLM-Friendly**: Tools designed for LLM to use intelligently

## Example Manifest File

```json
{
  "dataset_name": "Customer Demographics Analysis",
  "safe_name": "customer_demographics_analysis",
  "created_at": "2025-01-28T17:30:00",
  "workspace_root": "uploads/_workspaces/customer_demographics_analysis",
  "subdirectories": {
    "data": "uploads/_workspaces/customer_demographics_analysis/data",
    "models": "uploads/_workspaces/customer_demographics_analysis/models",
    "plots": "uploads/_workspaces/customer_demographics_analysis/plots",
    ...
  },
  "structure_version": "1.0"
}
```

## Technical Details

### Module: `dataset_workspace_manager.py`
Core functionality for workspace creation and file management.

### Module: `workspace_tools.py`
ADK-safe tool wrappers for LLM integration.

### Registration: `adk_safe_wrappers.py`
Tools registered as:
- `create_dataset_workspace_tool`
- `save_file_to_workspace_tool`
- `list_workspace_files_tool`
- `get_workspace_info_tool_v2`

## Future Enhancements

- Version control integration
- Workspace cleanup utilities
- Automatic workspace archival
- Cross-dataset file linking
- Workspace templates for common project types

