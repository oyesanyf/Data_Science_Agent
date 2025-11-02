# AutoGluon AutoML Integration Guide

## Overview

The Data Science Agent now includes **AutoGluon AutoML** capabilities for automated machine learning. AutoGluon automatically cleans data, selects features, trains multiple models, and creates ensembles.

## Features

### 1. **Automatic Data Cleaning** (`auto_clean_data`)
- Removes duplicates
- Handles missing values intelligently
- Removes columns with >50% missing data
- Fixes data types automatically

### 2. **Tabular AutoML** (`autogluon_automl`)
- **Automatic problem type detection** (classification/regression)
- **Trains multiple models**: LightGBM, XGBoost, CatBoost, Neural Networks, etc.
- **Creates ensembles** automatically
- **Feature importance** analysis
- **Presets**: `best_quality`, `high_quality`, `medium_quality`, `fast_training`

### 3. **Time Series Forecasting** (`autogluon_timeseries`)
- **Multiple forecasting models**: ARIMA, ETS, Theta, Deep Learning, Chronos-Bolt⚡
- **Automatic seasonality detection**
- **Probabilistic forecasts** (quantiles)
- **Chronos-Bolt presets**: `bolt_tiny`, `bolt_small`, `bolt_base` (fast, no GPU needed)
- **Original Chronos**: `chronos_tiny`, `chronos_small`, `chronos_large` (GPU recommended)

### 4. **Multimodal Learning** (`autogluon_multimodal`)
- **Handles images, text, and tabular data** together
- Deep learning models for complex datasets
- Automatic feature extraction

### 5. **Make Predictions** (`autogluon_predict`)
- Load trained models and make predictions on new data
- Includes prediction probabilities for classification

### 6. **Feature Importance** (`autogluon_feature_importance`)
- Understand which features drive predictions
- Automatic ranking of feature importance

## Quick Start Examples

### Example 1: Tabular Classification/Regression
```python
# User prompt to agent:
"Run AutoML on data.csv with target column 'price'"
```

The agent will:
1. Clean the data automatically
2. Detect it's a regression problem
3. Train 10+ models
4. Create an ensemble
5. Show leaderboard and best model

### Example 2: Time Series Forecasting
```python
# User prompt:
"Forecast sales for the next 7 days using sales_history.csv"
```

The agent will:
1. Load time series data
2. Train forecasting models (including Chronos-Bolt)
3. Generate 7-day forecasts with confidence intervals
4. Show model leaderboard

### Example 3: Clean Data First
```python
# User prompt:
"Clean the messy_data.csv file"
```

The agent will:
1. Remove duplicates
2. Handle missing values
3. Save cleaned data
4. Report statistics

## Installation

The dependencies are already added to `pyproject.toml`. Install them with:

```powershell
cd C:\harfile\data_science_agent
uv sync
```

This installs:
- `autogluon.tabular` - Tabular AutoML
- `autogluon.timeseries` - Time series forecasting
- `autogluon.multimodal` - Multimodal learning

## Usage with the Agent

### Running the Agent

```powershell
cd C:\harfile\data_science_agent

# CLI mode:
uv run adk run data_science

# Web UI mode:
uv run adk web
```

### Example Conversations

**1. Tabular AutoML:**
```
User: I have a CSV file called housing.csv with columns: 
      bedrooms, bathrooms, sqft, location, price. 
      Run AutoML to predict price with 10 minutes training.

Agent: [Uses autogluon_automl with time_limit=600]
       Result: Trained 12 models, best is WeightedEnsemble.
       Test accuracy: R² = 0.92
```

**2. Time Series Forecasting:**
```
User: Forecast daily electricity demand for next 48 hours.
      Data is in electricity.csv with columns: timestamp, item_id, demand.

Agent: [Uses autogluon_timeseries with prediction_length=48, presets='bolt_small']
       Result: Trained Chronos-Bolt and statistical models.
       Best: Chronos-Bolt (Small) with MASE = 0.78
```

**3. Data Cleaning:**
```
User: Clean raw_survey.csv - it has missing values and duplicates

Agent: [Uses auto_clean_data]
       Result: Removed 150 duplicates, handled 2,400 missing values.
       Cleaned file: raw_survey_cleaned.csv
```

## Tool Reference

### `auto_clean_data`
**Parameters:**
- `csv_path`: Path to input CSV
- `output_path`: (Optional) Path for cleaned CSV

**Example:**
```python
auto_clean_data('data/raw.csv', 'data/clean.csv')
```

---

### `autogluon_automl`
**Parameters:**
- `csv_path`: Training data path
- `target`: Target column name
- `task_type`: 'auto', 'classification', 'regression', 'binary', 'multiclass'
- `time_limit`: Training time in seconds (default: 600)
- `presets`: 'best_quality', 'high_quality', 'medium_quality', 'fast_training'
- `test_csv_path`: (Optional) Test data for evaluation
- `eval_metric`: (Optional) Custom metric

**Example:**
```python
autogluon_automl(
    csv_path='train.csv',
    target='sales',
    time_limit=300,
    presets='medium_quality',
    test_csv_path='test.csv'
)
```

---

### `autogluon_timeseries`
**Parameters:**
- `csv_path`: Time series data path
- `target`: Target column (default: 'target')
- `timestamp_col`: Timestamp column (default: 'timestamp')
- `item_id_col`: Series ID column (default: 'item_id')
- `prediction_length`: Forecast horizon (default: 24)
- `time_limit`: Training time in seconds (default: 600)
- `presets`: 'bolt_tiny', 'bolt_small', 'bolt_base', 'medium_quality', 'high_quality'
- `eval_metric`: (Optional) 'MASE', 'WQL', 'MAPE', 'RMSE'

**Example:**
```python
autogluon_timeseries(
    csv_path='sales.csv',
    target='sales',
    prediction_length=7,
    presets='bolt_small',
    eval_metric='MASE'
)
```

**Chronos-Bolt Presets:**
- `bolt_tiny`: Fastest, smallest (8M parameters)
- `bolt_small`: Good balance (48M parameters) - **Recommended**
- `bolt_base`: Most accurate (208M parameters)

All Chronos-Bolt models run on CPU without GPU.

---

### `autogluon_predict`
**Parameters:**
- `model_path`: Path to trained model directory
- `csv_path`: New data for prediction
- `output_path`: (Optional) Save predictions CSV

**Example:**
```python
autogluon_predict(
    model_path='./autogluon_models',
    csv_path='new_data.csv'
)
```

---

### `autogluon_feature_importance`
**Parameters:**
- `model_path`: Path to trained model directory
- `csv_path`: (Optional) Data for importance calculation

**Example:**
```python
autogluon_feature_importance(model_path='./autogluon_models')
```

---

### `autogluon_multimodal`
**Parameters:**
- `csv_path`: Training data path
- `label`: Label column name
- `image_col`: (Optional) Column with image paths
- `text_cols`: (Optional) List of text columns
- `time_limit`: Training time in seconds (default: 600)

**Example:**
```python
autogluon_multimodal(
    csv_path='pets.csv',
    label='adopted',
    image_col='photo_path',
    text_cols=['description'],
    time_limit=600
)
```

## Performance Tips

1. **Time Limits**: 
   - Quick test: 60-120 seconds
   - Production: 600-3600 seconds (10-60 minutes)
   - Best quality: 3600+ seconds

2. **Presets**:
   - Development/Testing: `fast_training`
   - Production: `medium_quality` or `high_quality`
   - Competitions: `best_quality`

3. **GPU Usage**:
   - Not required for Chronos-Bolt time series models
   - Helpful for original Chronos (large models)
   - Speeds up deep learning models (DeepAR, TFT)

4. **Memory**:
   - Large datasets: Increase system RAM
   - Time series: Chronos-Bolt uses less memory than original Chronos

## Automatic Workflow

The agent can automatically:
1. **Detect file upload** → Clean data
2. **Analyze columns** → Select target
3. **Choose task type** → Classification/Regression/Time Series
4. **Train models** → AutoML with ensemble
5. **Evaluate** → Test set performance
6. **Generate predictions** → On new data

## Troubleshooting

**Issue**: "AutoGluon not installed"
**Solution**: Run `uv sync` from the project directory

**Issue**: Time series format error
**Solution**: Ensure CSV has columns: `item_id`, `timestamp`, `target`

**Issue**: Out of memory
**Solution**: Reduce `time_limit` or use smaller presets

**Issue**: Slow training
**Solution**: Use `fast_training` preset or reduce `time_limit`

## Next Steps

1. **Install dependencies**: `uv sync`
2. **Start agent**: `uv run adk web`
3. **Upload a CSV** and ask: "Run AutoML on this data"
4. **Review results** and iterate

For detailed AutoGluon documentation: https://auto.gluon.ai/

