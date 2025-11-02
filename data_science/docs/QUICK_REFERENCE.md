# 🚀 Quick Reference Card - Data Science Agent

**URL:** http://localhost:8080

---

## 📋 Essential Commands

| What You Want | Just Say | Tool Used |
|---------------|----------|-----------|
| **See all tools** | "help" | `help()` |
| **List my files** | "list files" | `list_data_files()` |
| **Make charts** | "plot data" | `plot()` |
| **Get statistics** | "analyze data" | `analyze_dataset()` |
| **Clean data** | "clean data" | `auto_clean_data()` |
| **Train models (fast)** | "auto-sklearn on [target]" | `auto_sklearn_classify/regress()` |
| **Train models (best)** | "autogluon on [target]" | `smart_autogluon_automl()` |
| **Find groups** | "cluster into [N] groups" | `kmeans_cluster()` |
| **Find outliers** | "detect anomalies" | `isolation_forest_train()` |
| **Scale features** | "standardize data" | `scale_data()` |
| **Encode categories** | "encode data" | `encode_data()` |
| **Fill missing** | "fill missing values" | `impute_simple()` |
| **Pick best features** | "select top [N] features" | `select_features()` |

---

## 🎯 Common Workflows

### **Classification (Quick)**
```
1. Upload CSV
2. "plot data"
3. "auto-sklearn classify [target]"
   → Done in ~60 seconds!
```

### **Regression (Best Quality)**
```
1. Upload CSV
2. "clean data"
3. "autogluon regression on [target]"
   → Best accuracy in ~10 minutes
```

### **Clustering**
```
1. Upload CSV
2. "plot data"
3. "cluster into 3 groups"
4. "detect anomalies"
```

---

## 🔥 Speed vs Quality

| Tool | Speed | Accuracy | Use When |
|------|-------|----------|----------|
| **sklearn baseline** | ⚡ 5s | Good | Testing |
| **Auto-sklearn** | ⚡⚡ 60s | Better | Prototyping |
| **AutoGluon** | 🐢 600s | Best | Production |

---

## 📊 All 39 Tools by Category

### **🆘 Help (3)**
- `help()` - Show all tools
- `sklearn_capabilities()` - List sklearn models
- `suggest_next_steps()` - AI suggestions

### **📁 Files (2)**
- `list_data_files()` - List CSVs
- `save_uploaded_file()` - Save upload

### **🤖 AutoML - AutoGluon (4)**
- `smart_autogluon_automl()` - Train 9+ models
- `smart_autogluon_timeseries()` - Forecast
- `auto_clean_data()` - Fix data quality
- `list_available_models()` - Show models

### **🔬 AutoML - Auto-sklearn (2)**
- `auto_sklearn_classify()` - 5 classifiers + ensemble
- `auto_sklearn_regress()` - 6 regressors + ensemble

### **📈 Analysis & Viz (2)**
- `analyze_dataset()` - Full EDA
- `plot()` - 8 smart charts

### **🎓 Training (5)**
- `train()` - Generic training
- `train_classifier()` - Specific classifier
- `train_regressor()` - Specific regressor
- `grid_search()` - Hyperparameter tuning
- `evaluate()` - Cross-validation

### **🔮 Prediction (2)**
- `predict()` - Train & predict
- `classify()` - Quick classification

### **🎯 Clustering (4)**
- `kmeans_cluster()` - K-means
- `dbscan_cluster()` - Density-based
- `hierarchical_cluster()` - Hierarchical
- `isolation_forest_train()` - Anomaly detection

### **⚙️ Preprocessing (3)**
- `scale_data()` - Standardize/normalize
- `encode_data()` - One-hot encoding
- `expand_features()` - Polynomial features

### **🩹 Missing Data (3)**
- `impute_simple()` - Mean/median/mode
- `impute_knn()` - KNN imputation
- `impute_iterative()` - MICE

### **⭐ Feature Selection (3)**
- `select_features()` - SelectKBest
- `recursive_select()` - RFECV
- `sequential_select()` - Forward/backward

### **📊 Model Evaluation (3)**
- `split_data()` - Train/test split
- `grid_search()` - Tune hyperparameters
- `evaluate()` - Cross-validate

### **📝 Text (1)**
- `text_to_features()` - TF-IDF

### **🔧 Misc (2)**
- `auto_analyze_and_model()` - EDA + baseline
- `train_baseline_model()` - Quick baseline

---

## 💬 Natural Language Examples

```
✅ "train random forest on sales"
✅ "best quality model for price"
✅ "cluster my data"
✅ "fill missing with median"
✅ "detect outliers"
✅ "plot correlations"
✅ "clean and train on target"
```

**Just describe what you want - the agent figures out the tool!**

---

## 🎨 After Every Step

**Agent automatically suggests next actions:**

```
After plot:
  → "Try auto-sklearn for quick modeling?"
  → "Run AutoGluon for best accuracy?"
  → "Select important features first?"

After AutoML:
  → "Visualize feature importance?"
  → "Compare with sklearn models?"
  → "Try clustering to find patterns?"
```

---

## 📎 Artifacts

**All generated files appear in the UI:**
- 📊 Charts (.png)
- 📄 Cleaned data (.csv)
- 📈 Model results (.json)
- 🎯 Feature selections (.csv)

**Click 📎 to view/download!**

---

## 🚀 Pro Tips

1. **Let agent decide parameters** - Just say "train on X"
2. **Check suggestions** - Agent guides your workflow
3. **View artifacts** - Click 📎 after each step
4. **Try both AutoML** - Compare Auto-sklearn (fast) vs AutoGluon (best)
5. **Clean first** - Better results with clean data

---

## 📞 Get Help Anytime

```
User: "help"
→ Shows all 39 tools with examples

User: "what can you do?"
→ Lists capabilities

User: "suggest next steps"
→ AI-powered recommendations
```

---

## ⚡ Fastest Path to Results

```
1. Upload CSV (drag & drop)
2. "auto-sklearn on [target_column]"
3. Check artifacts
4. Done! (< 90 seconds total)
```

---

## 🎯 Most Popular Commands

1. `"plot data"` - Quick visualization
2. `"auto-sklearn on X"` - Fast AutoML
3. `"clean data"` - Fix quality issues
4. `"autogluon on X"` - Best models
5. `"cluster into N groups"` - Find patterns
6. `"detect anomalies"` - Find outliers
7. `"select top N features"` - Feature selection
8. `"analyze data"` - Full EDA

---

## 💰 Cost

**~$0.0007 per message** (OpenAI GPT-4o-mini)

Example session (10 steps): **~$0.007** (less than 1 cent!)

---

## 🎉 You're Ready!

**Open:** http://localhost:8080

**Upload a CSV and start with:** `"help"` or `"plot my data"`

**The agent will guide you from there!** 🚀

---

## 📚 Full Documentation

See `TOOLS_USER_GUIDE.md` for detailed examples of all 39 tools.

