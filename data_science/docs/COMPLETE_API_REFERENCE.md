# Complete AutoGluon API Reference

## ✅ All AutoGluon APIs Implemented

### 1. TabularPredictor ✅
**Implemented via:** `autogluon_automl()`, `train_specific_model()`

Full AutoML for tabular data with automatic model selection and ensembling.

**Usage:**
```python
# Full AutoML with all models
autogluon_automl(csv_path='data.csv', target='price', time_limit=600)

# Train specific model only
train_specific_model(csv_path='data.csv', target='price', model_type='GBM')
```

---

### 2. TabularDataset ✅
**Implemented via:** `autogluon_automl()`, `train_specific_model()`, `auto_clean_data()`

Automatic data loading and preprocessing.

**Features:**
- Automatic type inference
- Missing value handling
- Data cleaning
- Format conversion

---

### 3. Tabular Models ✅
**Implemented via:** `train_specific_model()`, `list_available_models()`

Individual model training with full control.

**Available Models:**
- **GBM** (LightGBM) - Fast gradient boosting
- **CAT** (CatBoost) - Best for categorical features
- **XGB** (XGBoost) - Powerful gradient boosting
- **RF** (Random Forest) - Ensemble of trees
- **XT** (Extra Trees) - Faster than Random Forest
- **NN_TORCH** (Neural Network) - Deep learning
- **LR** (Linear/Logistic Regression) - Fast baseline
- **KNN** (K-Nearest Neighbors) - Instance-based

**Usage:**
```python
# List all available models with descriptions
list_available_models()

# Train specific model with custom hyperparameters
train_specific_model(
    csv_path='data.csv',
    target='sales',
    model_type='GBM',
    hyperparameters={'num_boost_round': 100, 'learning_rate': 0.05}
)
```

---

### 4. MultiModalPredictor ✅
**Implemented via:** `autogluon_multimodal()`

Handle images, text, and tabular data together.

**Features:**
- Image classification/regression
- Text classification/sentiment analysis
- Multi-modal fusion (image + text + tabular)

**Usage:**
```python
autogluon_multimodal(
    csv_path='products.csv',
    label='category',
    image_col='image_path',
    text_cols=['description', 'title'],
    time_limit=600
)
```

---

### 5. TimeSeriesPredictor ✅
**Implemented via:** `autogluon_timeseries()`

Automated time series forecasting.

**Features:**
- Multiple forecasting models (ARIMA, ETS, Chronos-Bolt, Deep Learning)
- Probabilistic forecasts with quantiles
- Automatic seasonality detection
- Fast Chronos-Bolt models (no GPU needed)

**Usage:**
```python
# Forecast next 7 days using Chronos-Bolt
autogluon_timeseries(
    csv_path='sales_history.csv',
    target='sales',
    timestamp_col='date',
    item_id_col='store_id',
    prediction_length=7,
    presets='bolt_small',  # Fast, no GPU needed
    eval_metric='MASE'
)
```

---

### 6. TimeSeriesDataFrame ✅
**Implemented via:** `autogluon_timeseries()`

Specialized DataFrame for time series data.

**Features:**
- Multi-series support (panel data)
- Automatic frequency inference
- Time series validation
- Train/test splitting

---

### 7. Feature Generators ✅
**Implemented via:** `generate_features()`

Automatic feature engineering.

**Generated Features:**
- **Datetime**: year, month, day, hour, day_of_week, quarter, is_weekend
- **Text**: TF-IDF, bag of words, embeddings, sentiment
- **Numeric**: normalization, binning, polynomial features, interactions
- **Categorical**: one-hot encoding, frequency encoding, target encoding

**Usage:**
```python
# Generate all feature types
generate_features(
    csv_path='data.csv',
    enable_datetime=True,
    enable_text=True,
    enable_numeric=True,
    enable_category=True
)
```

**Example Output:**
```
Original features: 10
Generated features: 47
New features added: 37
- date → year, month, day, day_of_week, is_weekend
- description → text_tfidf_0, text_tfidf_1, ..., sentiment_score
- price → price_normalized, price_binned, price_log
```

---

### 8. FeatureMetadata ✅
**Implemented via:** `get_feature_metadata()`

Analyze and understand your dataset.

**Provided Information:**
- Feature types (numeric, categorical, datetime, text)
- Missing value statistics per column
- Unique value counts
- Data type recommendations
- Memory usage analysis

**Usage:**
```python
get_feature_metadata('data.csv')
```

**Example Output:**
```json
{
  "total_features": 15,
  "feature_types": {
    "int": ["age", "quantity", "id"],
    "float": ["price", "rating"],
    "category": ["product_type", "color"],
    "object": ["description", "name"],
    "datetime": ["purchase_date"]
  },
  "missing_values": {
    "age": 12,
    "rating": 5,
    "description": 0
  },
  "unique_counts": {
    "product_type": 5,
    "color": 8,
    "id": 1000
  },
  "memory_usage_mb": 2.45
}
```

---

### 9. Search Spaces (Hyperparameter Tuning) ✅
**Implemented via:** `customize_hyperparameter_search()`

Custom hyperparameter optimization.

**Search Strategies:**
- **auto**: Automatic selection
- **random**: Random search (fast)
- **bayes**: Bayesian optimization (efficient)
- **grid**: Grid search (exhaustive)

**Usage:**
```python
# Define custom search space
search_space = {
    'GBM': {
        'num_boost_round': [100, 200, 300, 500],
        'learning_rate': [0.001, 0.01, 0.05, 0.1],
        'max_depth': [3, 5, 7, 9],
    },
    'CAT': {
        'iterations': [100, 200, 500],
        'learning_rate': [0.01, 0.05, 0.1],
    }
}

# Run hyperparameter search
customize_hyperparameter_search(
    csv_path='data.csv',
    target='price',
    search_space=search_space,
    num_trials=20,
    searcher='bayes'  # Bayesian optimization
)
```

**Example Output:**
```json
{
  "status": "success",
  "best_model": "GBM",
  "best_hyperparameters": {
    "num_boost_round": 300,
    "learning_rate": 0.05,
    "max_depth": 7
  },
  "best_score": 0.92,
  "num_trials_completed": 20
}
```

---

## Complete Tool List

### Data Preparation
1. `auto_clean_data()` - Clean messy data
2. `generate_features()` - Feature engineering
3. `get_feature_metadata()` - Analyze dataset

### Model Training
4. `autogluon_automl()` - Full AutoML
5. `train_specific_model()` - Individual model
6. `autogluon_timeseries()` - Time series forecasting
7. `autogluon_multimodal()` - Multimodal learning

### Model Evaluation & Tuning
8. `autogluon_feature_importance()` - Feature importance
9. `customize_hyperparameter_search()` - HPO
10. `autogluon_predict()` - Make predictions

### Utilities
11. `list_available_models()` - Model catalog

---

## Agent Conversation Examples

### Example 1: Full AutoML Pipeline
```
User: I have sales_data.csv with columns: date, product, price, quantity, region.
      I want to predict quantity using all features.

Agent: [Executes pipeline]
       1. auto_clean_data() - Cleaned data
       2. get_feature_metadata() - Analyzed features
       3. generate_features() - Added datetime features from date
       4. autogluon_automl() - Trained 12 models
       
       Result: Best model is WeightedEnsemble with R² = 0.89
```

### Example 2: Specific Model Training
```
User: Train only a LightGBM model on my data with 500 boosting rounds.

Agent: train_specific_model(
         csv_path='data.csv',
         target='price',
         model_type='GBM',
         hyperparameters={'num_boost_round': 500}
       )
       
       Result: LightGBM trained. Test RMSE = 0.12
```

### Example 3: Time Series with Chronos-Bolt
```
User: Forecast daily sales for next 14 days using fast models.

Agent: autogluon_timeseries(
         csv_path='daily_sales.csv',
         prediction_length=14,
         presets='bolt_small'
       )
       
       Result: Chronos-Bolt (Small) selected. MASE = 0.73
               14-day forecast generated with confidence intervals.
```

### Example 4: Feature Engineering
```
User: Generate features from my dataset.

Agent: 1. get_feature_metadata() - Identified 3 datetime, 5 numeric, 2 text columns
       2. generate_features() - Created 42 new features
       
       New features include:
       - Datetime: year, month, day_of_week, quarter, is_weekend
       - Text: TF-IDF vectors, sentiment scores
       - Numeric: normalized values, binned categories
```

### Example 5: Hyperparameter Tuning
```
User: Find the best hyperparameters for XGBoost on my dataset.

Agent: customize_hyperparameter_search(
         model_type='XGB',
         search_space={
           'XGB': {
             'max_depth': [3, 5, 7, 9],
             'learning_rate': [0.01, 0.05, 0.1],
             'n_estimators': [100, 200, 500]
           }
         },
         num_trials=15,
         searcher='bayes'
       )
       
       Result: Best config - max_depth=7, lr=0.05, n_estimators=300
               Accuracy improved from 0.85 to 0.91
```

---

## Quick Reference Card

| Task | Tool | Time |
|------|------|------|
| Quick baseline | `train_specific_model(model_type='GBM')` | 1-2 min |
| Full AutoML | `autogluon_automl(presets='medium_quality')` | 10 min |
| Best quality | `autogluon_automl(presets='best_quality')` | 60+ min |
| Time series | `autogluon_timeseries(presets='bolt_small')` | 5 min |
| Feature engineering | `generate_features()` | 1 min |
| Hyperparameter tuning | `customize_hyperparameter_search()` | 10-30 min |

---

## All Features Checklist

- ✅ TabularPredictor (Full AutoML)
- ✅ TabularDataset (Data loading)
- ✅ Tabular Models (8 individual models: GBM, CAT, XGB, RF, XT, NN, LR, KNN)
- ✅ MultiModalPredictor (Image + Text + Tabular)
- ✅ TimeSeriesPredictor (ARIMA, ETS, Chronos-Bolt, Deep Learning)
- ✅ TimeSeriesDataFrame (Time series data structure)
- ✅ Feature Generators (Datetime, Text, Numeric, Categorical)
- ✅ FeatureMetadata (Dataset analysis)
- ✅ Search Spaces (Hyperparameter optimization with Bayesian/Grid/Random search)

## 🎉 All AutoGluon APIs Fully Implemented!

