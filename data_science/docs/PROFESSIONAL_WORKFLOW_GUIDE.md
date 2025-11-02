# 🎓 Professional Data Science Workflow Guide

## 📋 Overview

The Data Science Agent now follows an **industry-standard 11-stage workflow**. Each stage presents relevant tool options, and the user chooses which to execute. This ensures methodical, professional analysis with full user control.

---

## 🔄 The 11-Stage Workflow

### Stage 1: Data Collection & Ingestion 📥
**Purpose:** Gather and validate data from sources

**Available Tools:**
- `discover_datasets()` - Find available datasets with metadata
- `list_data_files()` - List all uploaded files
- `save_uploaded_file()` - Register new data source

**When to Use:**
- Starting a new project
- Need to locate existing datasets
- Multiple data sources to manage

---

### Stage 2: Data Cleaning & Preparation 🧹
**Purpose:** Handle missing values, outliers, inconsistencies; normalize and transform data

**Available Tools:**
- `robust_auto_clean_file()` - Comprehensive automatic cleaning (recommended!)
- `impute_simple(strategy='mean')` - Simple imputation (mean/median/mode)
- `impute_knn(n_neighbors=5)` - KNN-based imputation
- `remove_outliers(method='zscore')` - Outlier detection and removal
- `normalize()` - Min-max normalization
- `standardize()` - Z-score standardization
- `encode_categorical()` - Encode categorical variables

**When to Use:**
- After seeing data quality issues in EDA
- Before feature engineering
- Before modeling (data quality is critical!)

**Best Practice:** Run `robust_auto_clean_file()` first - it handles most issues automatically with intelligent strategies.

---

### Stage 3: Exploratory Data Analysis (EDA) 📊
**Purpose:** Understand data structure, distributions, and basic statistics

**Available Tools:**
- `describe()` - Descriptive statistics (mean, std, min, max, quartiles)
- `head(n=10)` - View first N rows
- `tail(n=10)` - View last N rows
- `shape()` - Dataset dimensions (rows × columns)
- `stats()` - Advanced statistical summary with missing values analysis
- `correlation_analysis()` - Correlation matrix and insights

**When to Use:**
- Immediately after file upload (Stage 1)
- After data cleaning to verify improvements
- Before making decisions about feature engineering

**Typical Sequence:**
1. `shape()` - Check dimensions
2. `describe()` - Get statistical overview
3. `head()` - View sample data
4. `stats()` - Deeper analysis if needed

---

### Stage 4: Visualization 📈
**Purpose:** Create plots, dashboards, and heatmaps for pattern discovery

**Available Tools:**
- `plot()` - Automatic intelligent plots (distribution, correlation, scatter)
- `correlation_plot()` - Correlation heatmap
- `plot_distribution(column='name')` - Distribution analysis for specific column
- `pairplot()` - Pairwise relationship plots

**When to Use:**
- After EDA to visualize patterns
- To identify relationships between variables
- To detect outliers visually
- For presentations and reports

**Best Practice:** Start with `plot()` - it generates multiple relevant plots automatically.

---

### Stage 5: Feature Engineering 🔧
**Purpose:** Generate new variables, apply scaling, encoding, dimensionality reduction

**Available Tools:**
- `select_features(target='column', k=10)` - Feature selection (SelectKBest)
- `expand_features(degree=2)` - Polynomial features
- `auto_feature_synthesis()` - Automatically generate derived features
- `apply_pca(n_components=0.95)` - Dimensionality reduction via PCA

**When to Use:**
- After cleaning and EDA
- Before modeling
- When you have too many features (dimensionality curse)
- To improve model performance

**Typical Sequence:**
1. `select_features()` - Identify most important features
2. `expand_features()` - Create polynomial features if needed
3. `apply_pca()` - Reduce dimensions if dataset is high-dimensional

---

### Stage 6: Statistical Analysis 📐
**Purpose:** Conduct hypothesis testing, measure relationships, assess significance

**Available Tools:**
- `stats()` - Inferential statistics
- `correlation_analysis()` - Detailed correlation with p-values
- `hypothesis_test()` - Statistical significance testing

**When to Use:**
- When you need to validate assumptions
- To test relationships between variables
- For scientific rigor in analysis
- Before making claims about data

---

### Stage 7: Machine Learning Model Development 🤖
**Purpose:** Train and tune algorithms for prediction/classification

**Available Tools:**

**AutoML (Recommended for beginners):**
- `autogluon_automl(target='column')` - Automatic ML (tries multiple models)
- `smart_autogluon_automl(target='column')` - Chunk-aware AutoML for large datasets

**Manual Training (More control):**
- `train_classifier(target='column', algorithm='random_forest')` - Classification
- `train_regressor(target='column', algorithm='random_forest')` - Regression

**Specific Algorithms:**
- `train_lightgbm_classifier(target='column')` - LightGBM (fast, accurate)
- `train_xgboost_classifier(target='column')` - XGBoost (powerful gradient boosting)
- `train_catboost_classifier(target='column')` - CatBoost (handles categorical well)

**When to Use:**
- After data is cleaned and features are engineered
- When you have a clear target variable
- Split: 80% train, 20% test (done automatically)

**Best Practice:**
1. Start with `autogluon_automl()` - it finds the best model automatically
2. If you need more control, use specific algorithms
3. **ALWAYS proceed to Stage 8 (Evaluation) after training!**

---

### Stage 8: Model Evaluation & Validation ✅
**Purpose:** Assess performance using metrics, cross-validation, interpretability

**Available Tools:**
- `accuracy()` - Accuracy metrics for your model
- `evaluate()` - Comprehensive evaluation (accuracy, precision, recall, F1, ROC-AUC, confusion matrix)
- `explain_model()` - Model interpretability (SHAP, LIME) - understand WHY the model predicts
- `feature_importance()` - Which features matter most
- `cross_validate()` - K-fold cross-validation for robust evaluation

**When to Use:**
- **MANDATORY after every model training** (Stage 7)
- Before deploying a model
- To compare different models
- When stakeholders ask "How good is the model?"

**Key Metrics:**
- **Accuracy:** Overall correctness (good for balanced datasets)
- **Precision:** Of predicted positives, how many are actually positive?
- **Recall:** Of actual positives, how many did we find?
- **F1-Score:** Harmonic mean of precision and recall
- **ROC-AUC:** Area under ROC curve (0.5 = random, 1.0 = perfect)
- **MSE/RMSE:** For regression - average squared error

**Typical Sequence:**
1. `evaluate()` - Get comprehensive metrics
2. `explain_model()` - Understand feature contributions
3. `feature_importance()` - See which features drive predictions

**Decision Points:**
- Accuracy < 70%: Go back to Stage 2 (Cleaning) or Stage 5 (Feature Engineering)
- Accuracy 70-85%: Try different algorithms or hyperparameter tuning
- Accuracy > 85%: Proceed to Stage 10 (Reporting) or Stage 9 (Deployment)

---

### Stage 9: Model Deployment (Optional) 🚀
**Purpose:** Deploy models, monitor drift, maintain performance

**Available Tools:**
- `export()` - Export trained model as pickle file
- `monitor_drift_fit()` - Set up data drift monitoring
- `monitor_drift_score()` - Check for distribution changes over time

**When to Use:**
- When model is ready for production
- Need to monitor model performance over time
- Deploying to APIs or services (outside this tool)

**Best Practice:**
1. Only deploy after thorough evaluation (Stage 8)
2. Set up drift monitoring to catch data changes
3. Retrain periodically based on drift detection

---

### Stage 10: Report and Insights 📄
**Purpose:** Summarize findings, highlight business implications, recommend actions

**Available Tools:**
- `export_executive_report()` - Generate comprehensive PDF report with visualizations, statistics, and model results
- `export_model_card()` - Model documentation (metadata, performance, intended use)
- `fairness_report()` - Fairness and bias analysis (important for ethical AI!)

**When to Use:**
- Final step after successful evaluation
- For presentations to stakeholders
- Documentation for compliance
- Sharing insights with non-technical audiences

**What's Included in Reports:**
- Dataset overview and statistics
- Visualizations (plots, heatmaps)
- Model performance metrics
- Feature importance
- Recommendations and next steps
- Fairness and bias analysis

**Typical Sequence:**
1. `export_executive_report()` - Main comprehensive report
2. `fairness_report()` - Check for bias if dealing with sensitive attributes
3. `export_model_card()` - Technical documentation

---

### Stage 11: Advanced & Specialized 🔬
**Purpose:** Specialized analyses beyond standard workflow

**Available Tools:**

**Causal Inference:**
- `causal_identify(treatment='X', outcome='Y')` - Identify causal relationships
- `causal_estimate(treatment='X', outcome='Y')` - Estimate treatment effects

**Data Drift:**
- `drift_profile()` - Comprehensive data drift profiling

**Time Series:**
- `ts_prophet_forecast(date_col='date', target='sales')` - Facebook Prophet forecasting
- `ts_backtest()` - Time series backtesting

**NLP & Embeddings:**
- `embed_text_column(text_col='description')` - Generate text embeddings
- `vector_search()` - Semantic search on embeddings

**When to Use:**
- When you need causal analysis (not just correlation)
- Time series prediction tasks
- Text data analysis
- Advanced drift detection

---

## 🔄 Example Complete Workflow

### Scenario: Predicting Customer Churn

**1. Stage 1: Data Collection**
```
User uploads customer_data.csv
→ analyze_dataset() runs automatically
→ Agent shows: "244 customers, 10 features detected"
```

**2. Stage 3: EDA**
```
Agent presents Stage 3 options:
  • describe()
  • head()
  • shape()
  • stats()

User chooses: describe()
→ Shows statistics for all columns
→ Notices: 15% missing values in 'income' column
```

**3. Stage 4: Visualization**
```
Agent presents Stage 4 options:
  • plot()
  • correlation_plot()

User chooses: plot()
→ Generates 4 plots automatically
→ Saved to Artifacts panel
```

**4. Stage 2: Data Cleaning**
```
Agent detects missing values, presents Stage 2 options:
  • robust_auto_clean_file() ← Recommended
  • impute_simple()
  • remove_outliers()

User chooses: robust_auto_clean_file()
→ Handles missing values with KNN imputation
→ Removes outliers
→ Encodes categorical variables
→ "Cleaning complete! 0% missing values remaining"
```

**5. Stage 3: Re-verify with EDA**
```
Agent presents Stage 3 options to verify cleaning:
  • stats()
  • describe()

User chooses: stats()
→ Confirms data quality improved
```

**6. Stage 5: Feature Engineering**
```
Agent presents Stage 5 options:
  • select_features()
  • expand_features()

User chooses: select_features(target='churn', k=8)
→ Selected top 8 features
→ "Feature importance scores calculated"
```

**7. Stage 7: Model Development**
```
Agent presents Stage 7 options:
  • autogluon_automl(target='churn') ← Recommended
  • train_classifier(target='churn')
  • train_lightgbm_classifier(target='churn')

User chooses: autogluon_automl(target='churn')
→ Training multiple models...
→ "Best model: WeightedEnsemble_L3"
→ "Preliminary accuracy: 87.2%"
```

**8. Stage 8: Evaluation (MANDATORY!)**
```
Agent MUST present Stage 8 options:
  • evaluate() ← Recommended
  • accuracy()
  • explain_model()
  • feature_importance()

User chooses: evaluate()
→ Shows comprehensive metrics:
   - Accuracy: 87.2%
   - Precision: 84.5%
   - Recall: 89.1%
   - F1-Score: 86.7%
   - ROC-AUC: 0.91
→ "Model performance is GOOD (>85%)!"
```

**9. Stage 8: Model Explainability**
```
Agent still in Stage 8, presents:
  • explain_model()
  • feature_importance()

User chooses: explain_model()
→ SHAP values calculated
→ "Top features: contract_type, tenure, monthly_charges"
→ "Customers with month-to-month contracts are 3x more likely to churn"
```

**10. Stage 10: Reporting**
```
Agent presents Stage 10 options:
  • export_executive_report()
  • export_model_card()
  • fairness_report()

User chooses: export_executive_report()
→ Generating PDF...
→ "Report saved: customer_churn_report_2025.pdf"
→ "Check Artifacts panel to download"
```

**11. Done!**
```
Agent: "Workflow complete! 🎉

Your churn prediction model:
✅ Accuracy: 87.2%
✅ ROC-AUC: 0.91
✅ Key insight: Contract type is the strongest predictor
✅ Report generated and ready to share

Next steps you could take:
  • Try different algorithms for comparison
  • Deploy model (Stage 9) with export()
  • Start new analysis with different target variable
  • Check fairness_report() for bias analysis

What would you like to do?"
```

---

## 📊 Stage Flow Decision Tree

```
File Upload
    ↓
Stage 1: Ingestion (auto: analyze_dataset)
    ↓
    ├─→ Stage 3: EDA ─────────────┐
    │       ↓                      │
    │   See data issues?           │
    │       ↓                      │
    │   Stage 4: Visualization ────┤
    │       ↓                      │
    │   Need cleaning?             │
    │       ↓                      │
    └─→ Stage 2: Cleaning ←───────┘
            ↓
        Verify cleaning?
            ↓
        Stage 3: EDA again
            ↓
        Ready for features?
            ↓
        Stage 5: Feature Engineering
            ↓
        Stage 7: Modeling
            ↓
        Stage 8: Evaluation ← MANDATORY!
            ↓
            ├─→ Results good (>85%)? ───→ Stage 10: Reporting
            │                                       ↓
            │                                   Done or Stage 9: Deploy
            │
            └─→ Results poor (<85%)? ───→ Back to Stage 2 or 5 or 7
```

---

## ✅ Best Practices

### 1. **Always Follow Stage Order (with flexibility)**
- Don't skip EDA (Stage 3) - you need to understand your data
- Don't skip Cleaning (Stage 2) if quality issues exist
- **NEVER skip Evaluation (Stage 8) after Modeling (Stage 7)**

### 2. **Iterate When Needed**
- Poor model performance? Go back to Stage 2 (Cleaning) or Stage 5 (Feature Engineering)
- After cleaning: Return to Stage 3 (EDA) to verify improvements
- Try multiple models in Stage 7, evaluate each in Stage 8

### 3. **Use AutoML First**
- `autogluon_automl()` is the best starting point - it tries many models automatically
- If you need more control, switch to specific algorithms
- Compare AutoML results with manual training

### 4. **Understand Your Metrics**
- Accuracy alone isn't enough - check precision, recall, F1
- For imbalanced datasets: Focus on F1-score and ROC-AUC
- For regression: Use RMSE and R²

### 5. **Document Everything**
- Use `export_executive_report()` for all projects
- Save model cards with `export_model_card()`
- Keep track of which stages you've completed

### 6. **Check for Bias**
- Run `fairness_report()` if your data includes sensitive attributes (gender, race, age)
- Ethical AI is responsible AI!

---

## 🎯 Quick Reference: Tool-to-Stage Mapping

| Tool | Stage | Purpose |
|------|-------|---------|
| `discover_datasets()` | 1 | Find data |
| `robust_auto_clean_file()` | 2 | Clean data |
| `describe()` | 3 | EDA statistics |
| `head()`, `tail()` | 3 | View data |
| `plot()` | 4 | Visualize patterns |
| `select_features()` | 5 | Feature engineering |
| `stats()` | 6 | Statistical analysis |
| `autogluon_automl()` | 7 | Train models |
| `evaluate()` | 8 | Evaluate performance |
| `export()` | 9 | Deploy model |
| `export_executive_report()` | 10 | Generate report |
| `causal_identify()` | 11 | Causal analysis |

---

## 🚀 Getting Started

1. **Upload your CSV file** to http://localhost:8080
2. **Review initial analysis** (Stage 1, automatic)
3. **Follow the agent's stage-based options**
4. **Choose tools one at a time**
5. **Never skip evaluation after modeling!**
6. **Generate final report when done**

---

## 💡 Remember

✅ The agent is your **guide**, not an automation  
✅ You **control** each step  
✅ Present **3-5 options** from appropriate stage  
✅ **Evaluation is mandatory** after modeling  
✅ Follow the **professional workflow** for best results  

**Your data science journey is now structured, professional, and under your complete control!** 🎓

