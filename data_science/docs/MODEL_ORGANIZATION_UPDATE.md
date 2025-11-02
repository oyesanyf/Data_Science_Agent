# Model Organization & Timestamp Update

## Summary

All models are now centrally organized under `data_science/models/` with project-based subdirectories and unique timestamped filenames. This provides:

✅ **Centralized Model Storage**: All models (sklearn, AutoGluon, etc.) in one location  
✅ **Project Organization**: Each dataset gets its own subdirectory  
✅ **Unique Timestamps**: No filename conflicts with automatic timestamps  
✅ **Easy Discovery**: Find all models for a specific dataset in one place  
✅ **Production Ready**: Automatic directory creation, safe naming, collision prevention  

---

## Directory Structure

```
data_science/
├── models/                                    # ✅ All models here
│   ├── <project_name_1>/                     # ✅ Each dataset gets a folder
│   │   ├── baseline_model_20250115_083045_a3f2.joblib     # sklearn models
│   │   ├── baseline_model_20250115_091230_b8e4.joblib     # Multiple timestamps OK
│   │   ├── autogluon_tabular_20250115_093015_c7d9/        # AutoGluon models
│   │   ├── autogluon_timeseries_20250115_101145_f2a8/
│   │   └── autogluon_multimodal_20250115_104520_e5c1/
│   │
│   ├── <project_name_2>/
│   │   ├── baseline_model_20250115_110035_d4b7.joblib
│   │   └── autogluon_hpo_20250115_112245_g9f3/
│   │
│   └── default/                              # Fallback if no project name
│       └── baseline_model_20250115_120045_h1a5.joblib
│
├── .uploaded/     # Uploaded CSV files
├── .plot/         # Generated plots
└── .export/       # PDF reports
```

---

## Project Naming

**Project names are automatically extracted from uploaded CSV filenames:**

| CSV Filename | Project Name | Model Directory |
|--------------|--------------|-----------------|
| `housing_data.csv` | `housing_data` | `data_science/models/housing_data/` |
| `sales-2024.csv` | `sales-2024` | `data_science/models/sales-2024/` |
| `iris.csv` | `iris` | `data_science/models/iris/` |
| `my_dataset!@#.csv` | `my_dataset___` | `data_science/models/my_dataset___/` (sanitized) |

**Sanitization Rules:**
- Only alphanumeric characters, underscores (`_`), and hyphens (`-`) are allowed
- All other characters are replaced with underscores
- Example: `sales@2024.csv` → `sales_2024`

---

## Timestamp Format

**All models use unique timestamps to prevent overwriting:**

```
<model_type>_<YYYYMMDD>_<HHMMSS>_<random_suffix>
```

**Examples:**
- `baseline_model_20250115_083045_a3f2.joblib`
- `autogluon_tabular_20250115_093015_c7d9/`
- `autogluon_timeseries_20250115_101145_f2a8/`

**Components:**
- `YYYYMMDD`: Date (e.g., `20250115` = January 15, 2025)
- `HHMMSS`: Time (e.g., `083045` = 08:30:45 AM)
- `random_suffix`: 4-character hex string (e.g., `a3f2`) to prevent collisions

---

## Code Changes

### 1. **`data_science/ds_tools.py`** - Core Helper Functions

#### Added Functions:

```python
def _get_project_name(csv_path: Optional[str] = None, dataset_name: Optional[str] = None) -> str:
    """Extract and sanitize project name from CSV path or dataset name."""
    if dataset_name:
        name = dataset_name
    elif csv_path:
        name = os.path.splitext(os.path.basename(csv_path))[0]
    else:
        name = "default"
    
    # Sanitize dataset name (remove special characters)
    name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
    return name

def _get_model_dir(csv_path: Optional[str] = None, dataset_name: Optional[str] = None) -> str:
    """Generate model directory path organized by dataset.
    
    Models are saved in: data_science/models/<project_name>/
    """
    project_name = _get_project_name(csv_path=csv_path, dataset_name=dataset_name)
    model_dir = os.path.join(MODELS_DIR, project_name)
    os.makedirs(model_dir, exist_ok=True)  # ✅ Auto-create if doesn't exist
    return model_dir

def _get_timestamped_model_path(
    csv_path: Optional[str] = None, 
    dataset_name: Optional[str] = None,
    model_type: str = "model",
    extension: str = ".joblib"
) -> str:
    """Generate a unique timestamped model path.
    
    Format: data_science/models/<project_name>/<model_type>_<timestamp><extension>
    Example: data_science/models/housing/baseline_model_20250115_083045_a3f2.joblib
    """
    model_dir = _get_model_dir(csv_path=csv_path, dataset_name=dataset_name)
    
    # Generate unique timestamp: YYYYMMDD_HHMMSS_XXXX (4-char random suffix)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(random.choices("0123456789abcdef", k=4))
    
    # Build filename: <model_type>_<timestamp>_<random_suffix><extension>
    filename = f"{model_type}_{timestamp}_{random_suffix}{extension}"
    
    return os.path.join(model_dir, filename)
```

#### Updated `train_baseline_model`:

**Before:**
```python
model_dir = _get_model_dir(csv_path)
model_path = os.path.join(model_dir, "baseline_model.joblib")  # ❌ Overwrites!
joblib.dump(pipe, model_path)
```

**After:**
```python
model_path = _get_timestamped_model_path(
    csv_path=csv_path,
    model_type="baseline_model",
    extension=".joblib"
)  # ✅ Unique timestamp
model_dir = os.path.dirname(model_path)
joblib.dump(pipe, model_path)
```

---

### 2. **`data_science/autogluon_tools.py`** - AutoGluon Models

#### Added Functions:

```python
# Centralized model directory (same as ds_tools.py)
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

def _get_project_name(csv_path: Optional[str] = None, dataset_name: Optional[str] = None) -> str:
    """Extract and sanitize project name from CSV path or dataset name."""
    # Same logic as ds_tools.py
    ...

def _get_autogluon_model_path(
    csv_path: Optional[str] = None, 
    dataset_name: Optional[str] = None,
    model_type: str = "autogluon"
) -> str:
    """Generate a unique timestamped AutoGluon model directory path.
    
    Format: data_science/models/<project_name>/<model_type>_<timestamp>_<random>/
    Example: data_science/models/housing/autogluon_20250115_083045_a3f2/
    """
    project_name = _get_project_name(csv_path=csv_path, dataset_name=dataset_name)
    project_dir = os.path.join(MODELS_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)
    
    # Generate unique timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(random.choices("0123456789abcdef", k=4))
    
    # Build directory name
    dirname = f"{model_type}_{timestamp}_{random_suffix}"
    
    model_path = os.path.join(project_dir, dirname)
    os.makedirs(model_path, exist_ok=True)  # ✅ Auto-create
    
    return model_path
```

#### Updated All AutoGluon Functions:

**Functions Updated:**
- `autogluon_automl` → Uses `autogluon_tabular` prefix
- `autogluon_timeseries` → Uses `autogluon_timeseries` prefix
- `autogluon_multimodal` → Uses `autogluon_multimodal` prefix
- `train_single_model` → Uses `autogluon_{model_type}` prefix
- `hyperparameter_tuning` → Uses `autogluon_hpo` prefix

**Before:**
```python
if output_dir is None:
    output_dir = './autogluon_models'  # ❌ Old location
os.makedirs(output_dir, exist_ok=True)
```

**After:**
```python
if output_dir is None:
    output_dir = _get_autogluon_model_path(
        csv_path=csv_path,
        model_type="autogluon_tabular"  # ✅ Type-specific
    )
```

---

### 3. **`.adkignore`** - Updated Ignore Rules

**Before:**
```
data_science/autogluon_models/  # Old location
data_science/models/            # New location
```

**After:**
```
# All models are now under data_science/models/ with project subdirectories
data_science/models/
```

---

## Usage Examples

### Example 1: Train Baseline Model

```python
# Upload housing_data.csv
# Project name: housing_data

result = await train_baseline_model(
    csv_path='data_science/.uploaded/housing_data.csv',
    target='price'
)

# Model saved to:
# data_science/models/housing_data/baseline_model_20250115_083045_a3f2.joblib
```

### Example 2: Train AutoGluon

```python
# Upload sales_2024.csv
# Project name: sales_2024

result = await smart_autogluon_automl(
    csv_path='data_science/.uploaded/sales_2024.csv',
    target='revenue',
    time_limit=300
)

# Model saved to:
# data_science/models/sales_2024/autogluon_tabular_20250115_093015_c7d9/
```

### Example 3: Multiple Training Runs (No Conflicts!)

```python
# First training run
train_baseline_model(csv_path='iris.csv', target='species')
# → data_science/models/iris/baseline_model_20250115_100000_a1b2.joblib

# Second training run (1 minute later)
train_baseline_model(csv_path='iris.csv', target='species')
# → data_science/models/iris/baseline_model_20250115_100100_c3d4.joblib

# Third training run (same second, different random suffix)
train_baseline_model(csv_path='iris.csv', target='species')
# → data_science/models/iris/baseline_model_20250115_100100_e5f6.joblib

# ✅ All models preserved, no overwriting!
```

### Example 4: Load Model by Project

```python
# List all models for housing_data project
load_model(dataset_name='housing_data')

# Returns:
# {
#   "model_directory": "data_science/models/housing_data/",
#   "available_models": [
#     "baseline_model_20250115_083045_a3f2.joblib",
#     "baseline_model_20250115_091230_b8e4.joblib",
#     "baseline_model_20250115_094815_c6d7.joblib"
#   ]
# }

# Load specific model
load_model(
    dataset_name='housing_data',
    model_filename='baseline_model_20250115_091230_b8e4.joblib'
)
```

---

## Benefits

### 1. **No More Overwriting**
- Each training run gets a unique timestamped filename
- Old models are preserved for comparison
- Supports multiple experiments per dataset

### 2. **Organized by Project**
- All models for a dataset are in one folder
- Easy to find and compare models for the same project
- Automatic cleanup by deleting entire project folder

### 3. **Production Ready**
- Automatic directory creation (no manual setup needed)
- Path traversal protection (sanitized filenames)
- Collision-resistant with random suffixes

### 4. **Multi-User Safe**
- Timestamps + random suffixes prevent collisions
- Works reliably even with concurrent training

### 5. **Easy Migration**
- Old models (if any) remain untouched in old locations
- New models automatically use new structure
- No breaking changes to existing code

---

## Migration Notes

### For Existing Projects:

**Old Structure:**
```
data_science/
├── autogluon_models/        # Old AutoGluon location
│   ├── model.pkl
│   └── ...
└── models/
    └── dataset1/
        └── baseline_model.joblib  # Old sklearn location
```

**New Structure:**
```
data_science/
└── models/                  # ✅ Everything under here now
    ├── dataset1/
    │   ├── baseline_model_20250115_083045_a3f2.joblib
    │   └── autogluon_tabular_20250115_093015_c7d9/
    └── dataset2/
        └── baseline_model_20250115_100045_d4b7.joblib
```

**No Action Required:**
- Old models remain functional in their old locations
- New models automatically use the new structure
- You can manually move old models to new structure if desired

---

## Testing

### Verify Directory Creation

```python
# Upload a file named "test_dataset.csv"
# Train a model
result = await train_baseline_model(
    csv_path='data_science/.uploaded/test_dataset.csv',
    target='target_column'
)

# Check result
print(result['model_directory'])
# → data_science/models/test_dataset/

print(result['model_path'])
# → data_science/models/test_dataset/baseline_model_20250115_120045_a3f2.joblib

# Verify directory exists
import os
os.path.exists(result['model_directory'])  # → True
os.path.exists(result['model_path'])        # → True
```

### Verify Timestamps

```python
import time

# Train first model
result1 = await train_baseline_model(csv_path='test.csv', target='target')
path1 = result1['model_path']

# Wait 2 seconds
time.sleep(2)

# Train second model
result2 = await train_baseline_model(csv_path='test.csv', target='target')
path2 = result2['model_path']

# Verify different paths
assert path1 != path2  # ✅ Different timestamps
```

---

## Validation

✅ **Syntax Validation**: All code passes `validate_code.py`  
✅ **Linter**: No errors in `uv lint`  
✅ **Import Check**: All modules import correctly  
✅ **Backward Compatible**: Existing code continues to work  
✅ **Directory Creation**: Auto-creates `data_science/models/` if missing  

---

## Updated: January 15, 2025

**Files Modified:**
- `data_science/ds_tools.py` - Added `_get_project_name`, `_get_model_dir`, `_get_timestamped_model_path`
- `data_science/autogluon_tools.py` - Added `_get_project_name`, `_get_autogluon_model_path`, updated all functions
- `.adkignore` - Updated to exclude new model directory

**Files Unchanged:**
- `data_science/chunk_aware_tools.py` - Passes through output_dir, works automatically
- `data_science/auto_sklearn_tools.py` - Doesn't save models yet

---

## See Also

- [`MODEL_ORGANIZATION_GUIDE.md`](MODEL_ORGANIZATION_GUIDE.md) - Original model organization guide
- [`TOOLS_USER_GUIDE.md`](TOOLS_USER_GUIDE.md) - Comprehensive tool documentation
- [`README.md`](README.md) - Main project documentation

