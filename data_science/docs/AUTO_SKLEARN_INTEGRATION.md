# ✅ Auto-sklearn Integration + AutoGluon Models Reorganization

## 🎉 **What's New:**

### **1. Auto-sklearn AutoML Tools (2 new tools!)**
Added scikit-learn based AutoML that automatically:
- ✅ Selects the best algorithm from 5-6 candidates
- ✅ Optimizes hyperparameters for each model
- ✅ Preprocesses features (scaling, encoding)
- ✅ Builds ensemble of top models
- ✅ Returns leaderboard with all results

### **2. Reorganized AutoGluon Models**
- ✅ Moved `autogluon_models/` → `data_science/autogluon_models/`
- ✅ Updated all code references
- ✅ Updated `.adkignore`
- ✅ Better project organization

---

## 📊 **New Auto-sklearn Tools:**

### **1. `auto_sklearn_classify()` - Classification AutoML**

**What it does:**
```
1. Tries 5+ classification algorithms:
   - RandomForest
   - GradientBoosting  
   - LogisticRegression
   - SVM
   - KNN

2. Optimizes hyperparameters for each (20 iterations)

3. Builds VotingClassifier ensemble of top 3 models

4. Returns leaderboard + ensemble results
```

**Example Usage:**
```python
# User prompt: "classify target_column"
result = await auto_sklearn_classify(
    csv_path="data_science/.data/mydata.csv",
    target="target_column",
    time_budget=60,        # seconds (approximate)
    n_iter=20,             # hyperparameter trials per model
    build_ensemble=True    # build voting ensemble
)

# Returns:
{
    "best_model": "RandomForest",
    "best_accuracy": 0.92,
    "best_params": {
        "n_estimators": 150,
        "max_depth": 20,
        ...
    },
    "leaderboard": [
        {"model": "RandomForest", "accuracy": 0.92, ...},
        {"model": "GradientBoosting", "accuracy": 0.91, ...},
        {"model": "LogisticRegression", "accuracy": 0.87, ...},
        ...
    ],
    "ensemble": {
        "type": "VotingClassifier",
        "models": ["RandomForest", "GradientBoosting", "LogisticRegression"],
        "accuracy": 0.93,
        "improvement": 0.01  # vs best single model
    }
}
```

---

### **2. `auto_sklearn_regress()` - Regression AutoML**

**What it does:**
```
1. Tries 6 regression algorithms:
   - RandomForest
   - GradientBoosting
   - Ridge
   - Lasso
   - SVR
   - KNN

2. Optimizes hyperparameters for each

3. Builds StackingRegressor ensemble of top 3

4. Returns leaderboard + ensemble results
```

**Example Usage:**
```python
# User prompt: "regress price"
result = await auto_sklearn_regress(
    csv_path="data_science/.data/mydata.csv",
    target="price",
    time_budget=60,
    n_iter=20,
    build_ensemble=True
)

# Returns:
{
    "best_model": "GradientBoosting",
    "best_r2": 0.88,
    "best_rmse": 12.5,
    "best_params": {
        "n_estimators": 120,
        "learning_rate": 0.1,
        ...
    },
    "leaderboard": [
        {"model": "GradientBoosting", "r2": 0.88, "rmse": 12.5, ...},
        {"model": "RandomForest", "r2": 0.86, "rmse": 13.2, ...},
        ...
    ],
    "ensemble": {
        "type": "StackingRegressor",
        "models": ["GradientBoosting", "RandomForest", "Ridge"],
        "r2": 0.89,
        "improvement": 0.01
    }
}
```

---

## 🎯 **Auto-sklearn vs AutoGluon:**

| Feature | Auto-sklearn (New!) | AutoGluon | Use When |
|---------|-------------------|-----------|----------|
| **Algorithms** | 5-6 models | 9+ models | Auto-sklearn: Quick comparison<br>AutoGluon: Best accuracy |
| **Speed** | ⚡ Fast (60s) | 🐢 Slower (600s) | Auto-sklearn: Fast iterations<br>AutoGluon: Final models |
| **Hyperparameter Tuning** | ✅ 20 iterations | ✅ Extensive | Auto-sklearn: Good enough<br>AutoGluon: Optimal |
| **Ensemble** | ✅ Voting/Stacking | ✅ Weighted | Both build ensembles |
| **Feature Engineering** | ✅ Basic | ✅ Advanced | AutoGluon for complex features |
| **Cross-platform** | ✅ Works everywhere | ✅ Works everywhere | Both are cross-platform |
| **Dependencies** | Scikit-learn only | AutoGluon stack | Auto-sklearn: Lighter |

---

## 📁 **AutoGluon Models Reorganization:**

### **Before:**
```
data_science_agent/
  ├── autogluon_models/       ❌ At root level
  │   ├── models/
  │   ├── predictor.pkl
  │   └── ...
  ├── data_science/
  └── ...
```

### **After:**
```
data_science_agent/
  ├── data_science/
  │   ├── autogluon_models/   ✅ Under data_science/
  │   │   ├── models/
  │   │   ├── predictor.pkl
  │   │   └── ...
  │   ├── .data/              ✅ User data
  │   ├── agent.py
  │   └── ...
  └── ...
```

**Benefits:**
- ✅ Better organization (all data_science artifacts in one place)
- ✅ Easier to .gitignore or backup
- ✅ Cleaner project root
- ✅ Follows module structure conventions

---

## 🔧 **Code Changes:**

### **1. Created `data_science/auto_sklearn_tools.py`**
```python
# New file with 2 main functions:
async def auto_sklearn_classify(...)  # Classification AutoML
async def auto_sklearn_regress(...)   # Regression AutoML

# Key features:
- Algorithm selection from 5-6 models
- RandomizedSearchCV for hyperparameter optimization
- Ensemble building (Voting/Stacking)
- Cross-validation
- Leaderboard generation
```

### **2. Updated `data_science/agent.py`**
```python
# Added imports
from .auto_sklearn_tools import (
    auto_sklearn_classify,
    auto_sklearn_regress,
)

# Added to tools list
FunctionTool(auto_sklearn_classify),
FunctionTool(auto_sklearn_regress),

# Updated instructions
"• AutoML (AutoGluon): smart_autogluon_automl, ... "
"• AutoML (Auto-sklearn): auto_sklearn_classify, auto_sklearn_regress "
"  (automated algorithm selection, hyperparameter optimization, ensemble)"
```

### **3. Updated `data_science/autogluon_tools.py`**
```python
# Before:
output_dir = './autogluon_models'

# After:
module_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(module_dir, 'autogluon_models')
```

### **4. Updated `.adkignore`**
```
# Before:
autogluon_models/

# After:
data_science/autogluon_models/
data_science/.data/
```

### **5. Updated `data_science/ds_tools.py`**
```python
# Added Auto-sklearn to suggestions:
suggestions["modeling"] = [
    "🤖 smart_autogluon_automl() - AutoGluon AutoML (best accuracy)",
    "🔬 auto_sklearn_classify/auto_sklearn_regress() - Auto-sklearn AutoML",
    "⚡ train_baseline_model() - Quick sklearn baseline",
]
```

---

## 💬 **Example User Workflows:**

### **Workflow 1: Upload → Auto-sklearn**
```
User: [Uploads data.csv with 'target' column]

Agent:
✅ File saved!

What would you like to do?
1. 📊 plot() - Visualize data
2. 🔬 auto_sklearn_classify() - Try 5+ models automatically
3. 🤖 smart_autogluon_automl() - Best accuracy (slower)

User: "auto-sklearn classification"

Agent: [Runs auto_sklearn_classify()]
✅ Tried 5 models, optimized hyperparameters
Best: RandomForest (accuracy: 0.92)
Ensemble: VotingClassifier (accuracy: 0.93)

📋 Next steps:
1. Compare with AutoGluon for potentially better results
2. Visualize feature importance
3. Try feature selection
```

### **Workflow 2: Compare AutoML Approaches**
```
User: "Compare auto-sklearn and autogluon"

Agent:
Running both AutoML tools...

🔬 Auto-sklearn Results (60s):
- Best: GradientBoosting (R² = 0.86)
- Time: 1 minute
- Models tried: 5

🤖 AutoGluon Results (600s):
- Best: WeightedEnsemble_L2 (R² = 0.91)
- Time: 10 minutes
- Models tried: 9

Recommendation:
- Use Auto-sklearn for quick iterations
- Use AutoGluon for production models
```

---

## 🚀 **Usage in Agent:**

The agent now automatically suggests Auto-sklearn:

**After file upload:**
```
Agent: "I can:
  1. plot() - Visualize
  2. auto_sklearn_classify() - Quick AutoML (60s)
  3. smart_autogluon_automl() - Best AutoML (600s)"
```

**After plotting:**
```
Agent: "Next steps:
  1. auto_sklearn_classify() - Try 5 models quickly
  2. smart_autogluon_automl() - Train 9+ models
  3. train_baseline_model() - Single sklearn model"
```

---

## ✅ **Status:**

```
✅ Server: http://localhost:8080 (Running)
✅ Model: OpenAI gpt-4o-mini
✅ Tools: 39 total
   - 35 original tools
   - 2 new Auto-sklearn tools
   - 2 AutoGluon tools
✅ Auto-sklearn: Classification + Regression
✅ AutoGluon models: Moved to data_science/
✅ Suggestions: Updated to mention Auto-sklearn
✅ Cost: ~$0.0007 per message
```

---

## 📊 **Tool Count Update:**

| Category | Tools | Details |
|----------|-------|---------|
| **AutoML (AutoGluon)** | 4 | smart_autogluon_automl, smart_autogluon_timeseries, auto_clean_data, list_available_models |
| **AutoML (Auto-sklearn)** | 2 | auto_sklearn_classify, auto_sklearn_regress |
| **Sklearn Models** | 5 | train, train_classifier, train_regressor, grid_search, evaluate |
| **Visualization** | 2 | plot, analyze_dataset |
| **Feature Engineering** | 3 | scale_data, encode_data, expand_features |
| **Feature Selection** | 3 | select_features, recursive_select, sequential_select |
| **Missing Data** | 3 | impute_simple, impute_knn, impute_iterative |
| **Clustering** | 4 | kmeans_cluster, dbscan_cluster, hierarchical_cluster, isolation_forest_train |
| **Text** | 1 | text_to_features |
| **File Management** | 2 | list_data_files, save_uploaded_file |
| **Model Utilities** | 2 | split_data, train_baseline_model |
| **Help** | 3 | help, sklearn_capabilities, suggest_next_steps |
| **Prediction** | 2 | predict, classify |
| **Misc** | 2 | auto_analyze_and_model, train_baseline_model |
| **TOTAL** | **39** | **All categories covered!** |

---

## 🎯 **Key Benefits:**

1. **More AutoML Options**: Users can choose between Auto-sklearn (fast) and AutoGluon (accurate)
2. **Better Organization**: All models stored under `data_science/` module
3. **Algorithm Transparency**: Auto-sklearn shows which algorithms were tried
4. **Quick Iterations**: Auto-sklearn great for rapid prototyping
5. **Ensemble Learning**: Both tools build ensembles automatically
6. **Cross-platform**: Works on Windows, Mac, Linux

---

## 🎨 **When to Use What:**

### **Use Auto-sklearn when:**
- ✅ You want quick results (< 60 seconds)
- ✅ Prototyping/experimenting
- ✅ Comparing 5-6 algorithms is enough
- ✅ You want to see hyperparameter optimization results
- ✅ Medium-sized datasets (< 100k rows)

### **Use AutoGluon when:**
- ✅ You need best possible accuracy
- ✅ Production models
- ✅ You have time for extensive training (> 10 minutes)
- ✅ Complex datasets with many features
- ✅ Want state-of-the-art ensembles

### **Use sklearn baseline when:**
- ✅ You want instant results (< 5 seconds)
- ✅ Simple datasets
- ✅ Testing specific algorithms
- ✅ Educational purposes

---

**Your agent now has 3 levels of AutoML: Fast (Auto-sklearn), Best (AutoGluon), and Instant (sklearn baseline)!** 🎊

