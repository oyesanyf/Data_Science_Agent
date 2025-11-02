# Model Organization & Loading Guide

## Overview

Models are now automatically organized by dataset in a structured directory hierarchy:

```
data_science/
└── models/
    ├── housing/
    │   ├── baseline_model.joblib
    │   ├── random_forest_model.joblib
    │   └── gradient_boost_model.joblib
    ├── iris/
    │   ├── baseline_model.joblib
    │   └── svm_model.joblib
    └── sales/
        └── baseline_model.joblib
```

## Features

✅ **Automatic Organization** - Models saved by dataset name  
✅ **Easy Loading** - Load models by dataset name  
✅ **Model Discovery** - List all models for a dataset  
✅ **Persistent Storage** - Models saved to disk permanently  
✅ **Clean Structure** - One subfolder per dataset  

## How It Works

### When You Train a Model

```python
# Train a model on housing.csv
train_baseline_model(target='price', csv_path='housing.csv')
```

**Result:**
- Model saved to: `data_science/models/housing/baseline_model.joblib`
- Returns: `{"model_path": "...", "model_directory": "data_science/models/housing/", ...}`

### Dataset Name Extraction

The system automatically extracts the dataset name from the CSV filename:
- `housing.csv` → `data_science/models/housing/`
- `sales_data.csv` → `data_science/models/sales_data/`
- `customer-info.csv` → `data_science/models/customer-info/`

Special characters are sanitized (only alphanumeric, `_`, and `-` allowed).

## Using load_model()

### Basic Usage

```python
# Load the baseline model for the housing dataset
load_model(dataset_name='housing')
```

**Returns:**
```json
{
  "status": "success",
  "message": "Model loaded successfully from ...",
  "model": <sklearn model object>,
  "model_path": "data_science/models/housing/baseline_model.joblib",
  "model_directory": "data_science/models/housing/",
  "model_size_mb": 0.15,
  "dataset_name": "housing",
  "available_models": ["baseline_model.joblib", "random_forest_model.joblib"]
}
```

### Load Specific Model File

```python
# Load a specific model file
load_model(
    dataset_name='housing',
    model_filename='random_forest_model.joblib'
)
```

### Load Model with Dataset

```python
# Load both model and dataset together
load_model(
    dataset_name='housing',
    csv_path='housing.csv'
)
```

**Returns (with dataset_info):**
```json
{
  "status": "success",
  "model": <model>,
  "model_path": "data_science/models/housing/baseline_model.joblib",
  "dataset_info": {
    "rows": 20640,
    "columns": 9,
    "column_names": ["longitude", "latitude", "housing_median_age", ...],
    "memory_mb": 1.45
  },
  "available_models": ["baseline_model.joblib", "random_forest_model.joblib"]
}
```

## Error Handling

### Model Not Found

```python
load_model(dataset_name='nonexistent')
```

**Returns:**
```json
{
  "error": "Model not found: data_science/models/nonexistent/baseline_model.joblib",
  "model_directory": "data_science/models/nonexistent/",
  "available_models": [],
  "hint": "Available models in 'nonexistent': No models found"
}
```

### Wrong Model Filename

```python
load_model(dataset_name='housing', model_filename='wrong.joblib')
```

**Returns:**
```json
{
  "error": "Model not found: data_science/models/housing/wrong.joblib",
  "available_models": ["baseline_model.joblib", "random_forest_model.joblib"],
  "hint": "Available models in 'housing': baseline_model.joblib, random_forest_model.joblib"
}
```

## Complete Workflow Examples

### Example 1: Train and Reload

```python
# 1. Train a model
train_baseline_model(target='price', csv_path='housing.csv')
# Model saved to: data_science/models/housing/baseline_model.joblib

# 2. Later... load the model
result = load_model(dataset_name='housing')
model = result['model']

# 3. Use the loaded model
predictions = model.predict(new_data)
```

### Example 2: Multiple Models Per Dataset

```python
# Train different models on the same dataset
train_baseline_model(target='price', csv_path='housing.csv')
# Saved as: data_science/models/housing/baseline_model.joblib

train_classifier(target='price_category', csv_path='housing.csv')
# Saved as: data_science/models/housing/model.joblib

# Load specific model
baseline = load_model(dataset_name='housing', model_filename='baseline_model.joblib')
classifier = load_model(dataset_name='housing', model_filename='model.joblib')
```

### Example 3: Model Discovery

```python
# Check what models are available
result = load_model(dataset_name='housing')

# See all available models
print(result['available_models'])
# ['baseline_model.joblib', 'random_forest_model.joblib', 'gradient_boost_model.joblib']
```

## Integration with Other Tools

### With AutoGluon

AutoGluon models are still saved to `data_science/autogluon_models/` (unchanged).

```python
# AutoGluon (separate directory)
smart_autogluon_automl(target='price', csv_path='housing.csv')
# Saved to: data_science/autogluon_models/

# Sklearn models (organized by dataset)
train_baseline_model(target='price', csv_path='housing.csv')
# Saved to: data_science/models/housing/
```

### With Export Tool

```python
# Train models
train_baseline_model(target='price', csv_path='housing.csv')
explain_model(target='price', csv_path='housing.csv')

# Export everything to PDF
export(title="Housing Analysis with Models")
# PDF includes all charts and analysis
```

## Directory Structure

```
data_science/
├── models/              # ← New: Sklearn models organized by dataset
│   ├── housing/
│   ├── iris/
│   └── sales/
├── autogluon_models/    # AutoGluon models (unchanged)
├── .uploaded/           # Uploaded CSV files
├── .plot/               # Generated plots
└── .export/             # PDF reports
```

## Model Persistence

### Automatic Saving

All sklearn-based training functions now automatically save models:
- `train_baseline_model()`
- `train_classifier()`
- `train_regressor()`
- `train()`
- `ensemble()`

Models are saved **both**:
1. **To disk** - `data_science/models/<dataset_name>/`
2. **As artifacts** - Available in UI Artifacts panel

### Model Files

Models are saved using `joblib`:
- Format: `.joblib` (efficient serialization)
- Includes: Full sklearn pipeline (preprocessing + model)
- Size: Typically 0.1-5 MB depending on complexity

## Advantages of This Structure

| Advantage | Description |
|-----------|-------------|
| **Organization** | One folder per dataset keeps things tidy |
| **Discovery** | Easy to see all models for a dataset |
| **Versioning** | Save multiple model versions per dataset |
| **Portability** | Copy entire dataset folder with all its models |
| **Clean URLs** | Clear path structure for model management |

## Commands Summary

| Action | Command |
|--------|---------|
| Train & save model | `train_baseline_model(target='y', csv_path='data.csv')` |
| Load default model | `load_model(dataset_name='data')` |
| Load specific model | `load_model(dataset_name='data', model_filename='rf.joblib')` |
| Load with dataset | `load_model(dataset_name='data', csv_path='data.csv')` |
| Check available models | `load_model(dataset_name='data')` → see `available_models` |

## Tips

1. **Use descriptive dataset names** - The CSV filename becomes the model directory name
2. **Save different model types** - Use different filenames for different algorithms
3. **Check available_models** - Always returned by `load_model()` to show what's available
4. **Load with dataset** - Specify `csv_path` to load both model and data together
5. **Model size** - Check `model_size_mb` to monitor storage usage

## Status

✅ **Implemented** - Model organization by dataset  
✅ **Implemented** - `load_model()` tool  
✅ **Implemented** - Logger import fix  
✅ **Updated** - `.adkignore` excludes `models/` directory  
✅ **Updated** - Agent instruction mentions `load_model`  
✅ **Ready to Use** - Server running with 44 tools  

## Related Documentation

- `TOOLS_USER_GUIDE.md` - All 44 tools documentation
- `SHAP_EXPLAINABILITY_GUIDE.md` - Model interpretation
- `EXPORT_TOOL_GUIDE.md` - PDF report generation

