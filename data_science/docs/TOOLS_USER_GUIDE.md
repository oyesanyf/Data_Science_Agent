# 📚 Complete Tools User Guide - All 39 Tools

**Your Data Science Agent has 39 powerful tools organized into 12 categories.**

---

## 🎯 Quick Start

**Access the agent:** http://localhost:8080

**Basic workflow:**
1. Upload CSV file
2. Agent auto-suggests tools
3. Use natural language commands
4. Check artifacts in UI

---

## 📖 Table of Contents

1. [Help & Discovery (3 tools)](#1-help--discovery-3-tools)
2. [File Management (2 tools)](#2-file-management-2-tools)
3. [AutoML - AutoGluon (4 tools)](#3-automl---autogluon-4-tools)
4. [AutoML - Auto-sklearn (2 tools)](#4-automl---auto-sklearn-2-tools)
5. [Analysis & Visualization (2 tools)](#5-analysis--visualization-2-tools)
6. [Training - Sklearn Models (5 tools)](#6-training---sklearn-models-5-tools)
7. [Prediction (2 tools)](#7-prediction-2-tools)
8. [Clustering (4 tools)](#8-clustering-4-tools)
9. [Data Preprocessing (3 tools)](#9-data-preprocessing-3-tools)
10. [Missing Data (3 tools)](#10-missing-data-3-tools)
11. [Feature Selection (3 tools)](#11-feature-selection-3-tools)
12. [Model Evaluation (3 tools)](#12-model-evaluation-3-tools)
13. [Text Processing (1 tool)](#13-text-processing-1-tool)
14. [Misc Tools (2 tools)](#14-misc-tools-2-tools)

---

## 1. Help & Discovery (3 tools)

### 1.1 `help()` - Show All Available Tools

**What it does:** Lists all 39 tools with descriptions and examples.

**Usage:**
```
User: "help"
User: "show me all tools"
User: "what can you do?"
```

**Example Response:**
```
Available Tools (39 total):

1. analyze_dataset - Extended EDA: schema, stats, correlations...
   Example: analyze_dataset(csv_path='.data/tips.csv')

2. plot - Generate 8 smart charts automatically
   Example: plot(csv_path='.data/tips.csv')

... (all 39 tools)
```

---

### 1.2 `sklearn_capabilities()` - List Sklearn Models

**What it does:** Shows all scikit-learn capabilities organized by task.

**Usage:**
```
User: "what sklearn models are available?"
User: "sklearn capabilities"
```

**Example Response:**
```json
{
  "classification": {
    "linear": ["LogisticRegression", "RidgeClassifier"],
    "tree": ["DecisionTreeClassifier", "RandomForestClassifier"],
    "ensemble": ["GradientBoostingClassifier", "AdaBoostClassifier"],
    "svm": ["SVC", "LinearSVC"],
    "naive_bayes": ["GaussianNB", "MultinomialNB"]
  },
  "regression": {
    "linear": ["LinearRegression", "Ridge", "Lasso"],
    "tree": ["DecisionTreeRegressor", "RandomForestRegressor"],
    "ensemble": ["GradientBoostingRegressor"],
    "svm": ["SVR"]
  },
  "clustering": ["KMeans", "DBSCAN", "AgglomerativeClustering"]
}
```

---

### 1.3 `suggest_next_steps()` - AI-Powered Suggestions

**What it does:** Suggests what to do next based on current task.

**Usage:**
```
User: "what should I do next?"
User: "suggest next steps"
```

**Example Response:**
```json
{
  "top_suggestions": [
    "📊 plot() - Create 8 smart charts",
    "🤖 smart_autogluon_automl() - Train models",
    "🔬 auto_sklearn_classify() - Quick AutoML"
  ],
  "all_categories": {
    "modeling": [...],
    "visualization": [...],
    "preprocessing": [...]
  }
}
```

---

## 2. File Management (2 tools)

### 2.1 `list_data_files()` - List Available CSV Files

**What it does:** Lists all CSV files in the `.data` directory.

**Usage:**
```
User: "list files"
User: "show me my data"
User: "what files do I have?"
```

**Example Response:**
```json
{
  "folder": "data_science/.data",
  "pattern": "*.csv",
  "files": [
    {
      "path": "data_science/.data/uploaded_123.csv",
      "name": "uploaded_123.csv",
      "size_bytes": 15234,
      "modified": "2025-10-15T20:30:00"
    },
    {
      "path": "data_science/.data/sales_data.csv",
      "name": "sales_data.csv",
      "size_bytes": 50000,
      "modified": "2025-10-15T19:00:00"
    }
  ]
}
```

---

### 2.2 `save_uploaded_file()` - Save CSV File

**What it does:** Saves uploaded CSV content to `.data` directory.

**Usage:**
```python
# Usually automatic when you upload via UI
# Can also be called programmatically:
save_uploaded_file(
    filename="mydata.csv",
    content="col1,col2\n1,2\n3,4"
)
```

**Example Response:**
```json
{
  "file_path": "data_science/.data/mydata.csv",
  "size_bytes": 28,
  "message": "File saved successfully"
}
```

---

## 3. AutoML - AutoGluon (4 tools)

### 3.1 `smart_autogluon_automl()` - AutoML Training

**What it does:** Trains 9+ models, builds ensemble, returns best model.

**Usage:**
```
User: "train model on target_column"
User: "num1 regression"
User: "predict sales using all features"
User: "best quality classification on is_fraud"
```

**Parameters:**
- `target`: Column to predict (auto-detected from prompt)
- `task_type`: "regression" or "classification" (auto-inferred)
- `time_limit`: Seconds (default 60, 120 if "best" mentioned)
- `presets`: "medium_quality", "best_quality", "fast_training"

**Example:**
```
User: "train regression on price with best quality"

Agent calls:
smart_autogluon_automl(
    csv_path="data_science/.data/uploaded_123.csv",
    target="price",
    task_type="regression",
    time_limit=120,
    presets="best_quality"
)
```

**Example Response:**
```json
{
  "status": "success",
  "best_model": "WeightedEnsemble_L2",
  "best_score": 0.92,
  "leaderboard": [
    {"model": "WeightedEnsemble_L2", "score": 0.92},
    {"model": "LightGBM", "score": 0.90},
    {"model": "CatBoost", "score": 0.89},
    ...
  ],
  "feature_importance": {
    "sqft": 0.35,
    "bedrooms": 0.25,
    "location": 0.20
  },
  "model_path": "data_science/autogluon_models",
  "message": "Training complete! Best model: WeightedEnsemble_L2"
}
```

---

### 3.2 `smart_autogluon_timeseries()` - Time Series Forecasting

**What it does:** Forecasts future values using time series models.

**Usage:**
```
User: "forecast sales for next 30 days"
User: "predict temperature for next week"
```

**Parameters:**
- `target`: Column to forecast
- `timestamp_column`: Date/time column
- `forecast_horizon`: Days to predict (default 7)
- `frequency`: "D" (daily), "H" (hourly), "M" (monthly)

**Example:**
```
User: "forecast sales for 30 days"

Agent calls:
smart_autogluon_timeseries(
    csv_path="data_science/.data/sales.csv",
    target="sales",
    timestamp_column="date",
    forecast_horizon=30,
    frequency="D"
)
```

---

### 3.3 `auto_clean_data()` - Automatic Data Cleaning

**What it does:** Fixes duplicates, missing values, outliers, data types.

**Usage:**
```
User: "clean my data"
User: "fix data quality issues"
User: "remove duplicates and handle missing values"
```

**Example:**
```
User: "clean the data"

Agent calls:
auto_clean_data(csv_path="data_science/.data/uploaded_123.csv")
```

**Example Response:**
```json
{
  "status": "success",
  "original_shape": [1000, 50],
  "cleaned_shape": [950, 48],
  "rows_removed": 50,
  "columns_removed": 2,
  "output_file": "data_science/.data/uploaded_123_cleaned.csv",
  "message": "Removed 50 duplicates, filled missing values, dropped 2 high-missing columns"
}
```

---

### 3.4 `list_available_models()` - Show AutoGluon Models

**What it does:** Lists all AutoGluon model types with descriptions.

**Usage:**
```
User: "what autogluon models are there?"
User: "show me available models"
```

**Example Response:**
```json
{
  "tabular_models": {
    "GBM": {
      "name": "LightGBM",
      "type": "Gradient Boosting",
      "pros": ["Fast", "High accuracy"],
      "cons": ["May overfit on small data"]
    },
    "CAT": {
      "name": "CatBoost",
      "pros": ["Handles categories natively"],
      "cons": ["Slower than LightGBM"]
    }
  },
  "timeseries_models": {
    "DeepAR": "RNN-based probabilistic forecasting",
    "ETS": "Exponential smoothing",
    "ARIMA": "Classic statistical forecasting"
  }
}
```

---

## 4. AutoML - Auto-sklearn (2 tools)

### 4.1 `auto_sklearn_classify()` - Classification AutoML

**What it does:** Tries 5 classifiers, optimizes hyperparameters, builds ensemble.

**Usage:**
```
User: "classify target_column with auto-sklearn"
User: "quick classification on is_fraud"
```

**Parameters:**
- `target`: Column to predict
- `time_budget`: Seconds (default 60)
- `n_iter`: Hyperparameter trials per model (default 20)
- `build_ensemble`: Build voting ensemble (default True)

**Example:**
```
User: "auto-sklearn classification on is_fraud"

Agent calls:
auto_sklearn_classify(
    csv_path="data_science/.data/transactions.csv",
    target="is_fraud",
    time_budget=60,
    n_iter=20,
    build_ensemble=True
)
```

**Example Response:**
```json
{
  "status": "success",
  "best_model": "RandomForest",
  "best_accuracy": 0.92,
  "best_params": {
    "n_estimators": 150,
    "max_depth": 20,
    "min_samples_split": 5
  },
  "leaderboard": [
    {"model": "RandomForest", "accuracy": 0.92, "cv_mean": 0.91},
    {"model": "GradientBoosting", "accuracy": 0.90, "cv_mean": 0.89},
    {"model": "LogisticRegression", "accuracy": 0.85, "cv_mean": 0.84},
    {"model": "SVM", "accuracy": 0.83, "cv_mean": 0.82},
    {"model": "KNN", "accuracy": 0.80, "cv_mean": 0.79}
  ],
  "ensemble": {
    "type": "VotingClassifier",
    "models": ["RandomForest", "GradientBoosting", "LogisticRegression"],
    "accuracy": 0.93,
    "improvement": 0.01
  },
  "message": "Best model: RandomForest (accuracy: 0.92)"
}
```

---

### 4.2 `auto_sklearn_regress()` - Regression AutoML

**What it does:** Tries 6 regressors, optimizes hyperparameters, builds stacking ensemble.

**Usage:**
```
User: "auto-sklearn regression on price"
User: "quick regression with auto-sklearn"
```

**Example:**
```
User: "auto-sklearn predict price"

Agent calls:
auto_sklearn_regress(
    csv_path="data_science/.data/houses.csv",
    target="price",
    time_budget=60,
    n_iter=20
)
```

**Example Response:**
```json
{
  "status": "success",
  "best_model": "GradientBoosting",
  "best_r2": 0.88,
  "best_rmse": 12.5,
  "best_params": {
    "n_estimators": 120,
    "learning_rate": 0.1,
    "max_depth": 5
  },
  "leaderboard": [
    {"model": "GradientBoosting", "r2": 0.88, "rmse": 12.5},
    {"model": "RandomForest", "r2": 0.86, "rmse": 13.2},
    {"model": "Ridge", "r2": 0.82, "rmse": 15.1},
    {"model": "Lasso", "r2": 0.80, "rmse": 16.0},
    {"model": "SVR", "r2": 0.78, "rmse": 17.2},
    {"model": "KNN", "r2": 0.75, "rmse": 18.5}
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

## 5. Analysis & Visualization (2 tools)

### 5.1 `analyze_dataset()` - Comprehensive EDA

**What it does:** Full statistical analysis, correlations, outliers, PCA, clustering.

**Usage:**
```
User: "analyze my data"
User: "show me statistics"
User: "exploratory data analysis"
```

**Example:**
```
User: "analyze the dataset"

Agent calls:
analyze_dataset(csv_path="data_science/.data/uploaded_123.csv")
```

**Example Response:**
```json
{
  "overview": {
    "shape": {"rows": 1000, "cols": 20},
    "memory_mb": 2.5,
    "dtypes": {
      "numeric": 15,
      "categorical": 3,
      "datetime": 2
    }
  },
  "numeric_stats": {
    "price": {
      "mean": 250000,
      "std": 50000,
      "min": 100000,
      "max": 500000,
      "missing": 0
    }
  },
  "correlations": {
    "strong_positive": [["sqft", "price", 0.85]],
    "strong_negative": [["age", "price", -0.65]]
  },
  "outliers": {
    "price": {"count": 15, "method": "IQR"}
  },
  "pca": {
    "variance_explained": [0.45, 0.25, 0.15]
  }
}
```

---

### 5.2 `plot()` - Auto-Generate 8 Charts

**What it does:** Creates distributions, heatmap, time series, boxplots, scatter plots.

**Usage:**
```
User: "plot the data"
User: "visualize my dataset"
User: "create charts"
```

**Example:**
```
User: "plot my data"

Agent calls:
plot(csv_path="data_science/.data/uploaded_123.csv", max_charts=8)
```

**Example Response:**
```json
{
  "artifacts": [
    "auto_corr_heatmap.png",
    "auto_hist_price.png",
    "auto_hist_sqft.png",
    "auto_boxplot_price_by_city.png",
    "auto_scatter_sqft_vs_price.png"
  ],
  "charts": [
    {"type": "correlation_heatmap", "columns": ["all_numeric"]},
    {"type": "histogram", "columns": ["price", "sqft"]},
    {"type": "boxplot", "x": "city", "y": "price"},
    {"type": "scatter", "x": "sqft", "y": "price"}
  ],
  "message": "Created 5 charts"
}
```

**Charts appear as artifacts in the UI!**

---

## 6. Training - Sklearn Models (5 tools)

### 6.1 `train()` - Generic Training

**What it does:** Trains model, auto-detects task type (classification/regression).

**Usage:**
```
User: "train model on target"
User: "quick training on price"
```

**Example:**
```
User: "train on sales"

Agent calls:
train(
    target="sales",
    csv_path="data_science/.data/data.csv",
    task="regression"  # auto-detected
)
```

---

### 6.2 `train_classifier()` - Train Specific Classifier

**What it does:** Trains a specific classification model.

**Usage:**
```
User: "train random forest classifier on is_fraud"
User: "logistic regression on target"
```

**Parameters:**
- `target`: Column to predict
- `model`: Full sklearn path (e.g., "sklearn.ensemble.RandomForestClassifier")

**Example:**
```
User: "train random forest on is_fraud"

Agent calls:
train_classifier(
    target="is_fraud",
    model="sklearn.ensemble.RandomForestClassifier",
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "model": "RandomForestClassifier",
  "accuracy": 0.92,
  "precision": 0.89,
  "recall": 0.87,
  "f1_score": 0.88,
  "confusion_matrix": [[850, 50], [30, 70]],
  "message": "Model trained successfully"
}
```

---

### 6.3 `train_regressor()` - Train Specific Regressor

**What it does:** Trains a specific regression model.

**Usage:**
```
User: "train gradient boosting regressor on price"
User: "ridge regression on sales"
```

**Example:**
```
User: "train ridge on price"

Agent calls:
train_regressor(
    target="price",
    model="sklearn.linear_model.Ridge",
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "model": "Ridge",
  "r2_score": 0.85,
  "rmse": 15.2,
  "mae": 12.3,
  "message": "Model trained successfully"
}
```

---

### 6.4 `grid_search()` - Hyperparameter Tuning

**What it does:** Searches for best hyperparameters using GridSearchCV.

**Usage:**
```
User: "optimize hyperparameters for random forest"
User: "grid search on target"
```

**Parameters:**
- `target`: Column to predict
- `model`: Model path
- `param_grid`: Dictionary of parameters to try

**Example:**
```python
grid_search(
    target="price",
    model="sklearn.ensemble.RandomForestRegressor",
    param_grid={
        "n_estimators": [50, 100, 200],
        "max_depth": [10, 20, None],
        "min_samples_split": [2, 5, 10]
    }
)
```

**Example Response:**
```json
{
  "best_params": {
    "n_estimators": 100,
    "max_depth": 20,
    "min_samples_split": 5
  },
  "best_score": 0.88,
  "cv_results": {...}
}
```

---

### 6.5 `evaluate()` - Cross-Validation

**What it does:** Evaluates model with cross-validation.

**Usage:**
```
User: "evaluate model on target"
User: "cross-validate on sales"
```

**Example Response:**
```json
{
  "cv_scores": [0.85, 0.87, 0.86, 0.88, 0.84],
  "mean_score": 0.86,
  "std_score": 0.015
}
```

---

## 7. Prediction (2 tools)

### 7.1 `predict()` - Train and Predict

**What it does:** Trains model and returns predictions + metrics.

**Usage:**
```
User: "predict target_column"
User: "make predictions on sales"
```

**Example:**
```
User: "predict price"

Agent calls:
predict(
    target="price",
    csv_path="data_science/.data/data.csv"
)
```

---

### 7.2 `classify()` - Classification Baseline

**What it does:** Quick classification baseline with LogisticRegression.

**Usage:**
```
User: "classify is_fraud"
User: "quick classification on target"
```

---

## 8. Clustering (4 tools)

### 8.1 `kmeans_cluster()` - K-Means Clustering

**What it does:** Groups data into K clusters.

**Usage:**
```
User: "cluster into 3 groups"
User: "kmeans clustering with 5 clusters"
```

**Parameters:**
- `n_clusters`: Number of clusters (default 3)

**Example:**
```
User: "cluster my data into 4 groups"

Agent calls:
kmeans_cluster(
    n_clusters=4,
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "n_clusters": 4,
  "cluster_sizes": [250, 300, 200, 250],
  "inertia": 1234.56,
  "silhouette_score": 0.45,
  "cluster_centers": [...],
  "message": "Created 4 clusters"
}
```

---

### 8.2 `dbscan_cluster()` - Density-Based Clustering

**What it does:** Finds clusters of varying shapes, detects outliers.

**Usage:**
```
User: "dbscan clustering"
User: "density-based clustering"
```

**Parameters:**
- `eps`: Maximum distance between points (default 0.5)
- `min_samples`: Minimum points per cluster (default 5)

**Example:**
```
User: "dbscan with eps=0.3"

Agent calls:
dbscan_cluster(
    eps=0.3,
    min_samples=5,
    csv_path="data_science/.data/data.csv"
)
```

---

### 8.3 `hierarchical_cluster()` - Hierarchical Clustering

**What it does:** Creates hierarchical tree of clusters.

**Usage:**
```
User: "hierarchical clustering with 3 clusters"
User: "agglomerative clustering"
```

**Parameters:**
- `n_clusters`: Number of clusters
- `linkage`: "ward", "complete", "average"

---

### 8.4 `isolation_forest_train()` - Anomaly Detection

**What it does:** Detects outliers/anomalies in data.

**Usage:**
```
User: "detect anomalies"
User: "find outliers"
```

**Parameters:**
- `contamination`: Expected proportion of outliers (default 0.1)

**Example:**
```
User: "detect anomalies in my data"

Agent calls:
isolation_forest_train(
    contamination=0.05,
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "n_anomalies": 50,
  "anomaly_percentage": 5.0,
  "anomaly_indices": [12, 45, 67, ...],
  "message": "Detected 50 anomalies (5.0%)"
}
```

---

## 9. Data Preprocessing (3 tools)

### 9.1 `scale_data()` - Feature Scaling

**What it does:** Standardizes or normalizes numeric columns.

**Usage:**
```
User: "scale my features"
User: "standardize the data"
User: "normalize columns"
```

**Parameters:**
- `scaler`: "StandardScaler", "MinMaxScaler", "RobustScaler"

**Example:**
```
User: "standardize my data"

Agent calls:
scale_data(
    scaler="StandardScaler",
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "scaler": "StandardScaler",
  "columns": ["price", "sqft", "age"],
  "artifact": "scaled.csv",
  "message": "Scaled 3 numeric columns"
}
```

**Saves:** `scaled.csv` as artifact

---

### 9.2 `encode_data()` - Categorical Encoding

**What it does:** One-hot encodes categorical variables.

**Usage:**
```
User: "encode categorical variables"
User: "one-hot encode the data"
```

**Example:**
```
User: "encode my data"

Agent calls:
encode_data(csv_path="data_science/.data/data.csv")
```

**Example Response:**
```json
{
  "categorical": ["city", "category"],
  "generated": ["city_NYC", "city_LA", "category_A", "category_B"],
  "artifact": "encoded.csv",
  "message": "Encoded 2 categorical columns into 4 binary columns"
}
```

**Saves:** `encoded.csv` with one-hot encoded features

---

### 9.3 `expand_features()` - Polynomial Features

**What it does:** Creates polynomial and interaction features.

**Usage:**
```
User: "create polynomial features"
User: "add interaction terms"
```

**Parameters:**
- `method`: "polynomial" or "interaction"
- `degree`: Polynomial degree (default 2)

**Example:**
```
User: "create polynomial features degree 2"

Agent calls:
expand_features(
    method="polynomial",
    degree=2,
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "method": "polynomial",
  "degree": 2,
  "original_features": 5,
  "new_features": 15,
  "artifact": "expanded.csv"
}
```

---

## 10. Missing Data (3 tools)

### 10.1 `impute_simple()` - Simple Imputation

**What it does:** Fills missing values with mean/median/mode.

**Usage:**
```
User: "fill missing values with median"
User: "impute missing data"
```

**Parameters:**
- `strategy`: "mean", "median", "most_frequent"

**Example:**
```
User: "fill missing values with median"

Agent calls:
impute_simple(
    strategy="median",
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "strategy": "median",
  "columns_imputed": ["price", "sqft", "age"],
  "values_filled": 45,
  "artifact": "imputed.csv"
}
```

---

### 10.2 `impute_knn()` - KNN Imputation

**What it does:** Uses K-nearest neighbors to impute missing values.

**Usage:**
```
User: "knn imputation"
User: "fill missing with knn"
```

**Parameters:**
- `n_neighbors`: Number of neighbors (default 5)

---

### 10.3 `impute_iterative()` - MICE Imputation

**What it does:** Iterative imputation (MICE algorithm).

**Usage:**
```
User: "mice imputation"
User: "iterative imputation"
```

---

## 11. Feature Selection (3 tools)

### 11.1 `select_features()` - SelectKBest

**What it does:** Selects top K features based on statistical tests.

**Usage:**
```
User: "select top 10 features"
User: "feature selection on target"
```

**Parameters:**
- `target`: Column to predict
- `k`: Number of features to select (default 10)

**Example:**
```
User: "select top 5 features for predicting price"

Agent calls:
select_features(
    target="price",
    k=5,
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "selected": ["sqft", "bedrooms", "bathrooms", "location_score", "age"],
  "scores": [125.3, 98.2, 87.1, 75.4, 62.3],
  "artifact": "selected_kbest.csv"
}
```

---

### 11.2 `recursive_select()` - Recursive Feature Elimination

**What it does:** Uses RFECV to recursively eliminate features.

**Usage:**
```
User: "recursive feature elimination on target"
User: "rfecv on sales"
```

**Example:**
```
User: "rfecv on price"

Agent calls:
recursive_select(
    target="price",
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "selected": ["sqft", "bedrooms", "location_score"],
  "n_features": 3,
  "artifact": "selected_rfecv.csv"
}
```

---

### 11.3 `sequential_select()` - Sequential Feature Selection

**What it does:** Forward or backward sequential feature selection.

**Usage:**
```
User: "forward feature selection on target"
User: "backward feature selection"
```

**Parameters:**
- `target`: Column to predict
- `direction`: "forward" or "backward"
- `n_features`: Number of features to select

---

## 12. Model Evaluation (3 tools)

### 12.1 `split_data()` - Train/Test Split

**What it does:** Splits data into training and test sets.

**Usage:**
```
User: "split data 80/20"
User: "create train test split"
```

**Parameters:**
- `target`: Column to predict
- `test_size`: Proportion for test set (default 0.2)

**Example:**
```
User: "split data on price with 70/30"

Agent calls:
split_data(
    target="price",
    test_size=0.3,
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "train_artifact": "train.csv",
  "test_artifact": "test.csv",
  "train_shape": [700, 20],
  "test_shape": [300, 20]
}
```

**Saves:** `train.csv` and `test.csv` as artifacts

---

### 12.2 `grid_search()` - Already covered in Section 6.4

---

### 12.3 `evaluate()` - Already covered in Section 6.5

---

## 13. Text Processing (1 tool)

### 13.1 `text_to_features()` - TF-IDF Vectorization

**What it does:** Converts text column to TF-IDF features.

**Usage:**
```
User: "convert text to features"
User: "tfidf on review_text"
```

**Parameters:**
- `text_column`: Column containing text
- `max_features`: Maximum number of features (default 100)

**Example:**
```
User: "convert review_text to tfidf features"

Agent calls:
text_to_features(
    text_column="review_text",
    max_features=50,
    csv_path="data_science/.data/reviews.csv"
)
```

**Example Response:**
```json
{
  "vocab_size": 50,
  "n_samples": 1000,
  "n_features": 50,
  "top_terms": ["good", "bad", "excellent", "poor", "quality"]
}
```

---

## 14. Misc Tools (2 tools)

### 14.1 `auto_analyze_and_model()` - Full Pipeline

**What it does:** Runs EDA + trains baseline model in one step.

**Usage:**
```
User: "analyze and train on target"
User: "full pipeline on sales"
```

**Example:**
```
User: "analyze and model price"

Agent calls:
auto_analyze_and_model(
    target="price",
    csv_path="data_science/.data/data.csv"
)
```

**Example Response:**
```json
{
  "eda": {
    "overview": {...},
    "correlations": {...}
  },
  "model": {
    "type": "Ridge",
    "r2_score": 0.82,
    "rmse": 18.5
  }
}
```

---

### 14.2 `train_baseline_model()` - Quick Baseline

**What it does:** Fast baseline with LogisticRegression/Ridge.

**Usage:**
```
User: "quick baseline on target"
User: "train baseline model"
```

---

## 🎯 Common Workflows

### Workflow 1: Complete Classification Project
```
1. Upload CSV file
   → File auto-saved to .data/

2. "analyze my data"
   → analyze_dataset()
   → Shows statistics, correlations, outliers

3. "plot the data"
   → plot()
   → Creates 8 charts as artifacts

4. "clean the data"
   → auto_clean_data()
   → Fixes quality issues

5. "classify target_column with auto-sklearn"
   → auto_sklearn_classify()
   → Tries 5 models, returns best

6. "compare with autogluon"
   → smart_autogluon_automl()
   → Trains 9+ models

7. "select top 5 features for target"
   → select_features()
   → Returns most important features
```

---

### Workflow 2: Quick Regression
```
1. Upload CSV
2. "predict price with auto-sklearn"
   → Auto-sklearn tries 6 regressors
3. "show feature importance"
4. Done! (< 2 minutes)
```

---

### Workflow 3: Clustering Analysis
```
1. Upload CSV
2. "plot my data"
   → Visualize distributions
3. "cluster into 4 groups"
   → kmeans_cluster(n_clusters=4)
4. "detect anomalies"
   → isolation_forest_train()
5. Done!
```

---

## 💡 Tips & Tricks

### Use Natural Language:
```
✅ "train random forest on sales"
✅ "best quality automl on price"
✅ "quick classification"
✅ "cluster my data into 3 groups"

❌ Don't need exact syntax:
   "smart_autogluon_automl(target='price', ...)"
```

---

### Agent Auto-Suggests:
After each step, agent suggests 2-3 next actions:
```
User: [Uploads file]

Agent:
"What would you like to do?
1. 📊 plot() - Visualize
2. 🔬 auto_sklearn_classify() - Quick AutoML
3. 🤖 smart_autogluon_automl() - Best AutoML"
```

---

### Check Artifacts:
All generated files appear as artifacts in the UI:
- Charts (.png files)
- Cleaned data (.csv files)
- Model results (.json files)

Click 📎 to view/download!

---

## 🚀 Quick Reference Card

| Task | Command | Tool |
|------|---------|------|
| **Show all tools** | "help" | `help()` |
| **List files** | "list files" | `list_data_files()` |
| **Visualize** | "plot data" | `plot()` |
| **Statistics** | "analyze data" | `analyze_dataset()` |
| **Clean data** | "clean data" | `auto_clean_data()` |
| **Quick AutoML** | "auto-sklearn on target" | `auto_sklearn_classify/regress()` |
| **Best AutoML** | "autogluon on target" | `smart_autogluon_automl()` |
| **Cluster** | "cluster into N groups" | `kmeans_cluster()` |
| **Anomalies** | "detect outliers" | `isolation_forest_train()` |
| **Scale** | "standardize data" | `scale_data()` |
| **Encode** | "encode categories" | `encode_data()` |
| **Fill missing** | "fill missing values" | `impute_simple()` |
| **Select features** | "select top N features" | `select_features()` |
| **Train model** | "train classifier on X" | `train_classifier()` |

---

## 📊 All 39 Tools At a Glance

```
✅ Help (3): help, sklearn_capabilities, suggest_next_steps
✅ Files (2): list_data_files, save_uploaded_file
✅ AutoGluon (4): smart_autogluon_automl, smart_autogluon_timeseries, 
                  auto_clean_data, list_available_models
✅ Auto-sklearn (2): auto_sklearn_classify, auto_sklearn_regress
✅ Viz (2): analyze_dataset, plot
✅ Train (5): train, train_classifier, train_regressor, grid_search, evaluate
✅ Predict (2): predict, classify
✅ Cluster (4): kmeans_cluster, dbscan_cluster, hierarchical_cluster, 
                isolation_forest_train
✅ Preprocess (3): scale_data, encode_data, expand_features
✅ Missing (3): impute_simple, impute_knn, impute_iterative
✅ Feature (3): select_features, recursive_select, sequential_select
✅ Evaluate (3): split_data, grid_search, evaluate
✅ Text (1): text_to_features
✅ Misc (2): auto_analyze_and_model, train_baseline_model
```

---

## 🎉 You Now Have 39 Powerful Tools!

**Access them all at:** http://localhost:8080

**Just ask in natural language - the agent knows what to do!** 🚀

