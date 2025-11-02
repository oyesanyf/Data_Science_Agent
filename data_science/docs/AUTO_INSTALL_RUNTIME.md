# Runtime Auto-Install System

## Overview

The Data Science Agent now includes a comprehensive **runtime auto-installation system** that automatically installs missing dependencies when tools are called. This eliminates the need for manual package installation and provides seamless user experience.

## How It Works

### Centralized Utility (`auto_install_utils.py`)

All auto-installation logic is centralized in `auto_install_utils.py`, which provides:

1. **Tool-to-Dependency Mapping**: Comprehensive mapping of 40+ tools to their required packages
2. **Smart Package Name Resolution**: Handles pip package names vs Python import names (e.g., `imbalanced-learn` → `imblearn`)
3. **Version Support**: Supports version specifications (e.g., `>=1.0.0`)
4. **Installation Caching**: Prevents redundant installation attempts
5. **Error Handling**: Provides detailed error messages if installation fails

### Key Functions

#### `ensure_package(package_name, pip_name=None, version=None, tool_name=None, silent=False)`

Ensures a package is available, auto-installing if needed.

```python
from .auto_install_utils import ensure_package

success, error = ensure_package('featuretools', pip_name='featuretools', version='>=1.0.0')
if not success:
    return {"error": error}
```

#### `ensure_tool_dependencies(tool_name, silent=False)`

Ensures all dependencies for a specific tool are available.

```python
from .auto_install_utils import ensure_tool_dependencies

success, error = ensure_tool_dependencies('auto_feature_synthesis', silent=False)
if not success:
    return {"error": error}
```

#### `auto_install_package(package_name, pip_name=None, version=None)` (Legacy)

Backward-compatible wrapper for existing code.

## Tool Dependencies Mapped

The system tracks dependencies for 40+ tools across categories:

### Feature Engineering
- `auto_feature_synthesis` → `featuretools>=1.0.0`
- `feature_importance_stability` → `featuretools>=1.0.0`

### Responsible AI
- `fairness_report` → `fairlearn>=0.9.0`
- `fairness_mitigation_grid` → `fairlearn>=0.9.0`

### Data & Model Drift
- `drift_profile` → `evidently>=0.4.0`
- `data_quality_report` → `evidently>=0.4.0`

### Causal Inference
- `causal_identify` → `dowhy>=0.11.0`
- `causal_estimate` → `dowhy>=0.11.0`

### Imbalanced Learning
- `rebalance_fit` → `imbalanced-learn>=0.11.0` (imports as `imblearn`)
- `calibrate_probabilities` → `imbalanced-learn>=0.11.0`

### Time Series
- `ts_prophet_forecast` → `prophet>=1.1.0`
- `ts_backtest` → `prophet>=1.1.0`

### Embeddings & Vector Search
- `embed_text_column` → `sentence-transformers>=2.0.0` (imports as `sentence_transformers`)
- `vector_search` → `faiss-cpu>=1.7.0` (imports as `faiss`)

### Data Versioning
- `dvc_init_local` → `dvc>=3.0.0`
- `dvc_track` → `dvc>=3.0.0`

### Post-Deploy Monitoring
- `monitor_drift_fit` → `alibi-detect>=0.11.0` (imports as `alibi_detect`)
- `monitor_drift_score` → `alibi-detect>=0.11.0`

### Fast Query & EDA
- `duckdb_query` → `duckdb>=0.9.0`
- `polars_profile` → `polars>=0.19.0`

### Hyperparameter Optimization
- `optuna_tune` → `optuna>=3.0.0`

### Data Validation
- `ge_auto_profile` → `great-expectations>=0.18.0` (imports as `great_expectations`)
- `ge_validate` → `great-expectations>=0.18.0`

### Experiment Tracking
- `mlflow_start_run` → `mlflow>=2.0.0`
- `mlflow_log_metrics` → `mlflow>=2.0.0`
- `mlflow_end_run` → `mlflow>=2.0.0`

### AutoML
- `smart_autogluon_automl` → `autogluon.tabular>=0.8.0` (imports as `autogluon`)
- `smart_autogluon_timeseries` → `autogluon.timeseries>=0.8.0`
- `auto_sklearn_classify` → `auto-sklearn>=0.15.0` (imports as `autosklearn`)
- `auto_sklearn_regress` → `auto-sklearn>=0.15.0`

### Deep Learning
- `train_dl_classifier` → `torch>=2.0.0`
- `train_dl_regressor` → `torch>=2.0.0`

## Implementation Status

### ✅ Completed
- `auto_install_utils.py` created with comprehensive dependency mapping
- `extended_tools.py` updated to use centralized utility:
  - `auto_feature_synthesis` ✅
  - `fairness_report` ✅
  - `drift_profile` ✅
  - `causal_identify` ✅
  - `rebalance_fit` ✅
  - `ts_prophet_forecast` ✅
- `adk_safe_wrappers.py` updated:
  - `auto_feature_synthesis_tool` ✅

### 🔄 Pending
- Update remaining tools in `extended_tools.py`
- Update `advanced_tools.py` (Optuna, Great Expectations, MLflow)
- Update `autogluon_tools.py`
- Update `deep_learning_tools.py`
- Update `advanced_modeling_tools.py`

## Usage Examples

### Example 1: Tool automatically installs dependency

```python
# User calls auto_feature_synthesis()
# System detects featuretools is missing
# Automatically runs: pip install featuretools>=1.0.0
# Tool proceeds after successful installation
```

### Example 2: Installation fails gracefully

```python
# If installation fails (e.g., network issues), tool returns:
{
    "status": "error",
    "error": "Featuretools is required but could not be installed: Installation failed",
    "__display__": "❌ Cannot use auto_feature_synthesis() - featuretools not available.\n\n**Error:** Installation failed\n\n**Manual Installation:**\n```bash\npip install featuretools\n```"
}
```

## Benefits

1. **Zero Configuration**: Users don't need to manually install packages
2. **Just-in-Time Installation**: Packages installed only when needed
3. **Clear Error Messages**: Helpful guidance if auto-install fails
4. **Centralized Management**: All dependency logic in one place
5. **Version Control**: Supports version specifications
6. **Performance**: Caching prevents redundant installation attempts

## Error Handling

If auto-installation fails, tools return user-friendly error messages with:
- Clear indication that a package is missing
- Specific error details
- Manual installation instructions
- Alternative tools if available

## Future Enhancements

- Add support for GPU-specific packages (e.g., `faiss-gpu` vs `faiss-cpu`)
- Add progress indicators for long installations
- Add installation timeout configuration
- Add batch installation for multiple tools
- Add dependency conflict detection

