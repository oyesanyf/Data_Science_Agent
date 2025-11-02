# ✅ Report Uses Model Results - How It Works

## Yes, the Report DOES Use Results from Models!

The `export_executive_report` function automatically collects and includes model training results in the report. Here's how:

## 🔍 How Model Results Are Collected

The report uses **3 priority levels** to find model results:

### **Priority 1: Workspace Outputs (Primary Source)**
```python
workspace_outputs = collect_workspace_outputs(tool_context=tool_context)
```
- Scans `workspace/reports/*_output_*.json` files
- Each tool execution saves its results as JSON (from `callbacks.py`)
- Extracts `metrics` from "Model Training" section outputs
- **Classification metrics:** accuracy, precision, recall, F1
- **Regression metrics:** R², MAE, RMSE

**Location:** Lines 8662-8725 in `ds_tools.py`

### **Priority 2: Training Artifact Markdown Files**
```python
# Look for training-related markdown files
*_train*.md, *_model*.md, *_autogluon*.md, *_sklearn*.md
```
- Parses markdown files in `workspace/artifacts/` and `workspace/reports/`
- Extracts metrics using regex patterns:
  - `accuracy: 0.95` or `test_acc: 0.95`
  - `r2: 0.92` or `r_squared: 0.92`
- **Location:** Lines 8728-8813 in `ds_tools.py`

### **Priority 3: Model Directory Metrics JSON**
```python
models_dir.rglob("*metrics*.json")
```
- Searches `workspace/models/` for `metrics.json` files
- Loads structured JSON with model performance metrics
- **Location:** Lines 8815-8871 in `ds_tools.py`

## 📊 What Model Results Are Included

### **For Classification Models:**
- **Accuracy** (e.g., 0.8523 = 85.23%)
- **Precision/F1 Score** (macro)
- **Recall**
- **Model Name** (e.g., "Random Forest", "AutoGluon Classifier")

### **For Regression Models:**
- **R² Score** (coefficient of determination)
- **MAE** (Mean Absolute Error)
- **RMSE** (Root Mean Squared Error)
- **Model Name** (e.g., "Gradient Boosting Regressor")

## 📝 Where Model Results Appear in Report

### **Section 5: Key Results**
- **Model Performance Summary Table**
  - Shows all trained models with their metrics
  - Organized as: `[Model Name, Metrics..., Status]`
- **Actual vs. Placeholder Data**
  - ✅ If models found: Shows **real metrics** from training
  - ❌ If no models: Shows warning with tool suggestions

**Location:** Lines 8645-8914 in `ds_tools.py`

### **Section 3E: Prediction Results**  
- Lists all prediction outputs from tools
- Includes target variable, task type, and metrics
- **Location:** Lines 8573-8618 in `ds_tools.py`

## 🔧 How Tools Save Results for Reports

Every tool execution saves results via `callbacks.py`:

```python
# In callbacks.py line 674-687
output_data = {
    "tool_name": tool_name,
    "timestamp": datetime.now().isoformat(),
    "status": result.get("status", "success"),
    "display": result.get("__display__"),
    "data": result,
    "artifacts": result.get("artifacts", []),
    "metrics": result.get("metrics", {})  # ← Model metrics saved here!
}
```

**Saved to:** `workspace/reports/{tool_name}_output_{timestamp}.json`

## ✅ Requirements for Report to Show Model Results

1. **Train at least one model** using:
   - `train_classifier()`
   - `train_regressor()`
   - `train_baseline_model()`
   - `smart_autogluon_automl()`
   - `auto_sklearn_classify()/regress()`
   - `ensemble()`

2. **Models must save metrics** (all training tools do this automatically)

3. **Run `export_executive_report()` AFTER training**

## 📋 Example Workflow

```python
# 1. Train a model
train_classifier(target="churn", csv_path="customer_data.csv")
# Result: Metrics saved to workspace/reports/train_classifier_tool_output_{timestamp}.json

# 2. Generate report (automatically finds model results)
export_executive_report(
    project_title="Customer Churn Prediction",
    target_variable="churn",
    csv_path="customer_data.csv"
)
# Result: Report includes actual accuracy, precision, recall from training
```

## 🎯 Summary

✅ **YES - Reports use model results!**
- Automatically scans workspace for training outputs
- Extracts metrics from JSON files, markdown artifacts, and metrics.json
- Displays actual model performance in "Key Results" section
- Shows warning if no models trained (with tool suggestions)

The report is **intelligent** - it finds model results automatically without manual input!

---

**Note:** The report checks multiple sources to ensure it finds model results even if saved in different locations.

