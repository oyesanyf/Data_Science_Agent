"""
AutoGluon-based AutoML tools for automated machine learning workflows.

This module provides automated data cleaning, feature selection, and model training
using AutoGluon for tabular, multimodal, and time series data.
"""

import os
import json
import time
import warnings
from pathlib import Path
from typing import Optional, Dict, Any, List
from io import BytesIO
from .ds_tools import ensure_display_fields

import pandas as pd
import numpy as np
from google.adk.tools import ToolContext

# Suppress pkg_resources deprecation warnings from AutoGluon (in worker processes too)
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*', category=UserWarning)
warnings.filterwarnings('ignore', message='.*pkg_resources.*', category=DeprecationWarning)

try:
    from autogluon.tabular import TabularPredictor, TabularDataset
    from autogluon.timeseries import TimeSeriesPredictor, TimeSeriesDataFrame
    # Skip MultiModalPredictor import to avoid transformers dependency issues
    MultiModalPredictor = None
    MULTIMODAL_AVAILABLE = False
    AUTOGLUON_AVAILABLE = True
except ImportError:
    AUTOGLUON_AVAILABLE = False
    MULTIMODAL_AVAILABLE = False
    MultiModalPredictor = None

# Import GPU configuration
try:
    from .gpu_config import GPU_AVAILABLE, get_gpu_params_autogluon, get_device_info
except ImportError:
    GPU_AVAILABLE = False
    def get_gpu_params_autogluon():
        return {}
    def get_device_info():
        return {'gpu_available': False}


def _json_safe(obj: Any) -> Any:
    """Convert complex Python objects to JSON-serializable types using production serializer."""
    from .json_serializer import to_json_safe
    return to_json_safe(obj, use_pydantic=True)


def _can_stratify(y, min_samples_per_class=2):
    """Check if stratification is safe for train_test_split.
    
    Stratification requires at least min_samples_per_class samples per class.
    
    Args:
        y: Target variable (pandas Series or numpy array)
        min_samples_per_class: Minimum samples required per class (default: 2)
    
    Returns:
        bool: True if stratification is safe, False otherwise
    """
    try:
        # Convert to pandas Series if needed for easier handling
        if isinstance(y, np.ndarray):
            y_series = pd.Series(y)
        else:
            y_series = y
        
        # Check if there are multiple classes
        unique_classes = y_series.nunique(dropna=True)
        if unique_classes < 2:
            return False
        
        # Check if each class has at least min_samples_per_class samples
        class_counts = y_series.value_counts()
        min_count = class_counts.min()
        
        return min_count >= min_samples_per_class
    except Exception:
        return False


def _get_original_dataset_name(csv_path: Optional[str] = None, tool_context: Optional['ToolContext'] = None) -> str:
    """
    Get the original dataset name - checks session FIRST, then falls back to path extraction.
    
    Priority:
        1. Session state (most accurate - set on upload)
        2. Extract from csv_path (strips timestamps)
        3. Default to "dataset"
    
    Args:
        csv_path: Path to CSV file
        tool_context: Tool context (to access saved original filename)
    
    Returns:
        Clean dataset name
    """
    # 🆕 PRIORITY 1: Check session for original uploaded filename
    if tool_context and hasattr(tool_context, 'state'):
        try:
            original_name = tool_context.state.get("original_dataset_name")
            if original_name:
                return original_name
        except Exception:
            pass
    
    # Fallback: Extract from path
    if csv_path:
        return _extract_dataset_name(csv_path)
    
    return "dataset"


def _extract_dataset_name(csv_path: str) -> str:
    """
    Extract original dataset name from filepath, stripping timestamp prefixes and suffixes.
    
    This function preserves the ORIGINAL dataset name across all transformations:
    - Strips upload timestamps (uploaded_<timestamp>_)
    - Strips processing timestamps (<timestamp>_)
    - Strips suffixes (_cleaned, _features, _scaled, etc.)
    
    Examples:
        "uploaded_1760564375_customer_data.csv" → "customer_data"
        "1760564375_sales_data.csv" → "sales_data"
        "uploaded_1760595115.csv" → "data"  (fallback when no original name)
        "1760597406_uploaded_1760595115_cleaned.csv" → "data"
        "customer_data_cleaned.csv" → "customer_data"
        "1760597406_data_cleaned_features.csv" → "data"
    
    Args:
        csv_path: Path to CSV file
    
    Returns:
        Clean dataset name (just the original base name)
    """
    import re
    from pathlib import Path
    
    # Get filename without extension
    filename = Path(csv_path).stem
    
    # Store original for fallback
    original_filename = filename
    
    # Step 1: Strip ALL timestamp prefixes (can have multiple layers)
    # Pattern: "uploaded_<timestamp>_" or "<timestamp>_"
    while True:
        prev = filename
        # Remove "uploaded_<timestamp>_" prefix
        filename = re.sub(r'^uploaded_\d{10,}_', '', filename)
        # Remove "<timestamp>_" prefix
        filename = re.sub(r'^\d{10,}_', '', filename)
        # If nothing changed, we're done stripping prefixes
        if filename == prev:
            break
    
    # Step 2: Strip common suffixes (_cleaned, _features, _scaled, etc.)
    suffixes_to_remove = [
        '_cleaned', '_features', '_scaled', '_encoded', 
        '_imputed', '_selected', '_pca', '_test', '_train',
        '_temp', '_temporal'
    ]
    
    for suffix in suffixes_to_remove:
        filename = filename.replace(suffix, '')
    
    # Step 3: If name is now empty or just generic words, find the real dataset name
    excluded_words = ['uploaded', 'temp', 'test', 'data', 'file', 'csv']
    
    if not filename or filename.lower() in excluded_words:
        # Try to find the FIRST meaningful alphabetic part from original filename
        # Extract all alphabetic portions (ignore numbers)
        alpha_parts = re.findall(r'[a-zA-Z]+', original_filename)
        
        # Find first meaningful word (not in excluded list)
        for word in alpha_parts:
            if word.lower() not in excluded_words and len(word) > 1:
                filename = word
                break
        
        # If still nothing found, use "dataset" as ultimate fallback
        if not filename or filename.lower() in excluded_words:
            filename = "dataset"
    
    return filename


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Automatic data cleaning for a dataframe.
    
    Steps:
    - Remove duplicate rows
    - Handle missing values with smart imputation
    - Remove columns with too many missing values (>50%)
    - Fix data types
    """
    df = df.copy()
    
    # Remove duplicates
    initial_rows = len(df)
    df = df.drop_duplicates()
    duplicates_removed = initial_rows - len(df)
    
    # Remove columns with >50% missing values
    missing_pct = df.isnull().sum() / len(df)
    cols_to_drop = missing_pct[missing_pct > 0.5].index.tolist()
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
    
    # Handle remaining missing values
    # Numeric columns: fill with median
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())
    
    # Categorical columns: fill with mode or 'Unknown'
    cat_cols = df.select_dtypes(include=['object', 'category']).columns
    for col in cat_cols:
        if df[col].isnull().any():
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val[0])
            else:
                df[col] = df[col].fillna('Unknown')
    
    return df


@ensure_display_fields
async def auto_clean_data(
    csv_path: str,
    output_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """Clean CSV: remove duplicates, handle missing values, fix types."""
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed. Run: pip install autogluon.tabular"}
    
    # Load data
    df = pd.read_csv(csv_path)
    initial_shape = df.shape
    
    # Clean
    df_clean = _clean_dataframe(df)
    final_shape = df_clean.shape
    
    # Save cleaned data with original dataset name preserved
    if output_path is None:
        # Extract original dataset name (strips timestamp prefixes)
        clean_name = _extract_dataset_name(csv_path)
        
        # Build output path with timestamp + original name + _cleaned
        timestamp = int(time.time())
        output_filename = f"{timestamp}_{clean_name}_cleaned.csv"
        output_path = str(Path(csv_path).parent / output_filename)
    
    df_clean.to_csv(output_path, index=False)
    
    result = {
        "status": "success",
        "input_file": csv_path,
        "output_file": output_path,
        "original_shape": initial_shape,
        "cleaned_shape": final_shape,
        "rows_removed": initial_shape[0] - final_shape[0],
        "columns_removed": initial_shape[1] - final_shape[1],
        "message": f"Cleaned data saved to {output_path}"
    }
    
    # Save artifact if tool_context available
    if tool_context is not None:
        from google.genai import types
        buf = BytesIO()
        df_clean.to_csv(buf, index=False)
        await tool_context.save_artifact(
            filename=Path(output_path).name,
            artifact=types.Part.from_bytes(
                data=buf.getvalue(),
                mime_type="text/csv"
            )
        )
    
    return _json_safe(result)


@ensure_display_fields
async def autogluon_automl(
    csv_path: str = "",
    target: str = "",
    task_type: str = "auto",
    time_limit: int = 600,
    presets: str = "medium_quality",
    output_dir: Optional[str] = None,
    test_csv_path: Optional[str] = None,
    eval_metric: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """AutoML: train 10+ models, auto-detect task type, create ensemble. Best for tabular ML."""
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed. Run: pip install autogluon.tabular"}
    
    try:
        #  ENHANCED: Auto-find most recent CSV if no path provided
        if not csv_path:
            from .smart_file_finder import _find_available_csvs
            available_files = _find_available_csvs(limit=5)
            if not available_files:
                return {
                    "error": "No CSV file specified and none found",
                    "message": "Please provide csv_path or upload a CSV file first"
                }
            csv_path = available_files[0]["path"]
            print(f"[OK] Auto-selected most recent file: {available_files[0]['filename']}")
        
        #  ENHANCED: Smart file discovery if file not found
        if not os.path.exists(csv_path):
            from .smart_file_finder import _find_available_csvs, _suggest_best_match
            available_files = _find_available_csvs(limit=10)
            best_match = _suggest_best_match(csv_path, available_files)
            
            if best_match:
                csv_path = best_match
                print(f"[OK] Found similar file: {os.path.basename(csv_path)}")
            else:
                return {
                    "error": f"File not found: {csv_path}",
                    "available_files": [f["filename"] for f in available_files],
                    "message": f"File not found. Available files: {[f['filename'] for f in available_files[:5]]}"
                }
        
        # Load and clean data
        full_data = TabularDataset(csv_path)
        full_data = _clean_dataframe(full_data)
        
        # Validate target column
        if target not in full_data.columns:
            return {
                "error": f"Target column '{target}' not found. Available columns: {list(full_data.columns)}"
            }
        
        # [OK] Automatically split into train/test (80/20) if no test set provided
        if test_csv_path is None:
            from sklearn.model_selection import train_test_split
            
            # Split data
            train_data, test_data = train_test_split(
                full_data, 
                test_size=0.2, 
                random_state=42,
                stratify=full_data[target] if _can_stratify(full_data[target]) else None
            )
            
            # Save test set to temporary file for evaluation
            test_temp_path = csv_path.replace('.csv', '_test_temp.csv')
            test_data.to_csv(test_temp_path, index=False)
            test_csv_path = test_temp_path
            auto_split = True
        else:
            # User provided test set
            train_data = full_data
            auto_split = False
        
        # Set output directory (data_science/models/<filename>/autogluon)
        if output_dir is None:
            # Get original dataset name (checks session first, then extracts from path)
            dataset_name = _get_original_dataset_name(csv_path, tool_context)
            
            # Sanitize dataset name
            dataset_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in dataset_name)
            
            # Save in data_science/models/<dataset_name>/autogluon/
            module_dir = os.path.dirname(os.path.abspath(__file__))
            models_dir = os.path.join(module_dir, 'models', dataset_name)
            output_dir = os.path.join(models_dir, 'autogluon')
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure predictor
        predictor_args = {
            "label": target,
            "path": output_dir,
        }
        
        if eval_metric:
            predictor_args["eval_metric"] = eval_metric
        
        predictor = TabularPredictor(**predictor_args)
        
        # Get GPU parameters if available
        gpu_params = get_gpu_params_autogluon()
        device_info = get_device_info()
        
        # Log GPU status
        if GPU_AVAILABLE:
            print(f" GPU MODE: Training AutoGluon with {device_info.get('device_name', 'GPU')}")
        else:
            print(" CPU MODE: Training AutoGluon on CPU")
        
        # Train models with GPU support
        fit_kwargs = {
            'train_data': train_data,
            'presets': presets,
            'time_limit': time_limit,
        }
        fit_kwargs.update(gpu_params)  # Add GPU params if available
        
        predictor.fit(**fit_kwargs)
        
        # Get leaderboard
        leaderboard = predictor.leaderboard(silent=True)
        
        # Prepare results
        result = {
            "status": "success",
            "model_path": output_dir,
            "target": target,
            "problem_type": predictor.problem_type,
            "best_model": predictor.model_best,
            "num_models_trained": len(leaderboard),
            "training_time": time_limit,
            "leaderboard": leaderboard.to_dict(),
            "n_samples_train": len(train_data),   # [OK] NEW
            "n_samples_total": len(full_data) if auto_split else len(train_data),  # [OK] NEW
            "test_split": "80/20 (automatic)" if auto_split else "user-provided",  # [OK] NEW
        }
        
        # [OK] Evaluate on test set (now always available)
        if test_csv_path:
            test_data_eval = TabularDataset(test_csv_path)
            test_data_eval = _clean_dataframe(test_data_eval)
            
            if target in test_data_eval.columns:
                # Evaluate
                eval_results = predictor.evaluate(test_data_eval, silent=True)
                result["test_evaluation"] = eval_results
                result["n_samples_test"] = len(test_data_eval)  # [OK] NEW
                
                # Generate predictions
                y_pred = predictor.predict(test_data_eval.drop(columns=[target]))
                result["test_predictions"] = {
                    "sample_predictions": y_pred.head(10).tolist(),
                    "num_predictions": len(y_pred)
                }
        
        # Feature importance
        try:
            feature_importance = predictor.feature_importance(test_data if test_csv_path else train_data)
            result["feature_importance"] = feature_importance.to_dict()
        except Exception:
            pass
        
        # Save artifacts
        if tool_context is not None:
            from google.genai import types
            
            # Save leaderboard
            lb_json = json.dumps(result["leaderboard"], default=str)
            await tool_context.save_artifact(
                filename="autogluon_leaderboard.json",
                artifact=types.Part.from_bytes(
                    data=lb_json.encode("utf-8"),
                    mime_type="application/json"
                )
            )
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "AutoML training failed. Check your data and parameters."
        }


@ensure_display_fields
async def autogluon_predict(
    model_path: str,
    csv_path: str,
    output_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """Load trained model and make predictions on new data."""
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed. Run: pip install autogluon.tabular"}
    
    try:
        # Load model
        predictor = TabularPredictor.load(model_path)
        
        # Load data
        data = TabularDataset(csv_path)
        data = _clean_dataframe(data)
        
        # Make predictions
        predictions = predictor.predict(data)
        
        # Get prediction probabilities if classification
        try:
            pred_probs = predictor.predict_proba(data)
            has_probs = True
        except Exception:
            pred_probs = None
            has_probs = False
        
        # Save predictions
        if output_path is None:
            base = Path(csv_path).stem
            output_path = str(Path(csv_path).parent / f"{base}_predictions.csv")
        
        results_df = data.copy()
        results_df['prediction'] = predictions
        
        if has_probs and pred_probs is not None:
            for col in pred_probs.columns:
                results_df[f'prob_{col}'] = pred_probs[col]
        
        results_df.to_csv(output_path, index=False)
        
        result = {
            "status": "success",
            "model_path": model_path,
            "input_file": csv_path,
            "output_file": output_path,
            "num_predictions": len(predictions),
            "sample_predictions": predictions.head(20).tolist(),
        }
        
        # Save artifact
        if tool_context is not None:
            from google.genai import types
            buf = BytesIO()
            results_df.to_csv(buf, index=False)
            await tool_context.save_artifact(
                filename=Path(output_path).name,
                artifact=types.Part.from_bytes(
                    data=buf.getvalue(),
                    mime_type="text/csv"
                )
            )
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Prediction failed. Check model path and input data."
        }


@ensure_display_fields
async def autogluon_feature_importance(
    model_path: str,
    csv_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Get feature importance from a trained AutoGluon model.
    
    Args:
        model_path: Path to saved AutoGluon model directory
        csv_path: Optional path to CSV for importance calculation
        tool_context: ADK tool context for artifact saving
    
    Returns:
        Dictionary with feature importance rankings
    
    Example:
        autogluon_feature_importance(model_path='data_science/autogluon_models')
    """
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed. Run: pip install autogluon.tabular"}
    
    try:
        # Load model
        predictor = TabularPredictor.load(model_path)
        
        # Get feature importance
        if csv_path:
            data = TabularDataset(csv_path)
            data = _clean_dataframe(data)
            feature_importance = predictor.feature_importance(data)
        else:
            feature_importance = predictor.feature_importance()
        
        result = {
            "status": "success",
            "model_path": model_path,
            "feature_importance": feature_importance.to_dict(),
            "top_features": feature_importance.head(10).to_dict(),
        }
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to compute feature importance."
        }


@ensure_display_fields
async def autogluon_timeseries(
    csv_path: str,
    target: str = "target",
    timestamp_col: str = "timestamp",
    item_id_col: str = "item_id",
    prediction_length: int = 24,
    time_limit: int = 600,
    presets: str = "medium_quality",
    output_dir: Optional[str] = None,
    test_csv_path: Optional[str] = None,
    eval_metric: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """Forecast time series: ARIMA, Chronos-Bolt, Deep Learning. Use presets='bolt_small' for fast CPU forecasting."""
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed. Run: pip install autogluon.timeseries"}
    
    try:
        # Load full time series data
        full_df = pd.read_csv(csv_path)
        full_data = TimeSeriesDataFrame.from_data_frame(
            full_df,
            id_column=item_id_col,
            timestamp_column=timestamp_col
        )
        
        # [OK] Automatically split into train/test (temporal split - last 20% of time) if no test set provided
        if test_csv_path is None:
            # Calculate split point (80% for training, 20% for testing)
            timestamps = pd.to_datetime(full_df[timestamp_col])
            split_time = timestamps.quantile(0.8)
            
            # Split data temporally (earlier data = training, later data = test)
            train_df = full_df[timestamps <= split_time]
            test_df = full_df[timestamps > split_time]
            
            # Convert to TimeSeriesDataFrame
            train_data = TimeSeriesDataFrame.from_data_frame(
                train_df,
                id_column=item_id_col,
                timestamp_column=timestamp_col
            )
            test_data = TimeSeriesDataFrame.from_data_frame(
                test_df,
                id_column=item_id_col,
                timestamp_column=timestamp_col
            )
            
            # Save test set to temporary file for consistency
            test_temp_path = csv_path.replace('.csv', '_test_temporal.csv')
            test_df.to_csv(test_temp_path, index=False)
            test_csv_path = test_temp_path
            auto_split = True
        else:
            # User provided test set
            train_data = full_data
            test_data = None
            auto_split = False
        
        # Set output directory
        if output_dir is None:
            # Get original dataset name (checks session first, then extracts from path)
            dataset_name = _get_original_dataset_name(csv_path, tool_context)
            
            # Sanitize dataset name
            dataset_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in dataset_name)
            
            # Save in data_science/models/<dataset_name>/autogluon_timeseries/
            module_dir = os.path.dirname(os.path.abspath(__file__))
            models_dir = os.path.join(module_dir, 'models', dataset_name)
            output_dir = os.path.join(models_dir, 'autogluon_timeseries')
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure predictor
        predictor_args = {
            "prediction_length": prediction_length,
            "path": output_dir,
            "target": target,
        }
        
        if eval_metric:
            predictor_args["eval_metric"] = eval_metric
        
        predictor = TimeSeriesPredictor(**predictor_args)
        
        # Train models
        predictor.fit(
            train_data=train_data,
            presets=presets,
            time_limit=time_limit,
        )
        
        # Get leaderboard
        leaderboard = predictor.leaderboard(silent=True)
        
        # Generate predictions
        predictions = predictor.predict(train_data)
        
        # Prepare results
        result = {
            "status": "success",
            "model_path": output_dir,
            "target": target,
            "prediction_length": prediction_length,
            "best_model": predictor.model_best,
            "num_models_trained": len(leaderboard),
            "training_time": time_limit,
            "leaderboard": leaderboard.to_dict(),
            "sample_predictions": predictions.head(20).to_dict(),
            "n_samples_train": len(train_data),  # [OK] NEW
            "n_samples_total": len(full_data) if auto_split else len(train_data),  # [OK] NEW
            "test_split": "80/20 temporal (automatic)" if auto_split else "user-provided",  # [OK] NEW
        }
        
        # [OK] Evaluate on test set (now always available for automatic splits)
        if test_csv_path:
            if test_data is None:
                # Load user-provided test set
                test_data = TimeSeriesDataFrame.from_data_frame(
                    pd.read_csv(test_csv_path),
                    id_column=item_id_col,
                    timestamp_column=timestamp_col
                )
            
            # Evaluate
            eval_results = predictor.evaluate(test_data, silent=True)
            result["test_evaluation"] = eval_results
            result["n_samples_test"] = len(test_data)  # [OK] NEW
            
            # Generate test predictions
            test_predictions = predictor.predict(test_data)
            result["test_predictions"] = {
                "sample_predictions": test_predictions.head(20).to_dict(),
                "num_predictions": len(test_predictions)
            }
        
        # Save artifacts
        if tool_context is not None:
            from google.genai import types
            
            # Save predictions
            buf = BytesIO()
            predictions.to_csv(buf)
            await tool_context.save_artifact(
                filename="timeseries_predictions.csv",
                artifact=types.Part.from_bytes(
                    data=buf.getvalue(),
                    mime_type="text/csv"
                )
            )
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Time series forecasting failed. Check your data format."
        }


@ensure_display_fields
async def autogluon_multimodal(
    csv_path: str,
    label: str,
    image_col: Optional[str] = None,
    text_cols: Optional[List[str]] = None,
    time_limit: int = 600,
    output_dir: Optional[str] = None,
    test_csv_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Automated multimodal learning using AutoGluon MultiModalPredictor.
    
    Handles datasets with images, text, and tabular features automatically.
    
    Args:
        csv_path: Path to training CSV file
        label: Name of the label column to predict
        image_col: Optional name of column containing image paths
        text_cols: Optional list of text column names
        time_limit: Training time limit in seconds (default 600)
        output_dir: Directory to save models (defaults to './autogluon_mm_models')
        test_csv_path: Optional path to test CSV for evaluation
        tool_context: ADK tool context for artifact saving
    
    Returns:
        Dictionary with model performance and predictions
    
    Example:
        autogluon_multimodal(csv_path='pets.csv', label='adopted', 
                            image_col='image_path', time_limit=300)
    """
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed. Run: pip install autogluon.multimodal"}
    
    if not MULTIMODAL_AVAILABLE or MultiModalPredictor is None:
        return {"error": "AutoGluon MultiModal not available. MultiModalPredictor import failed."}
    
    try:
        # Load data
        train_data = pd.read_csv(csv_path)
        
        # Set output directory (organized by dataset)
        if output_dir is None:
            dataset_name = _get_original_dataset_name(csv_path, tool_context)
            dataset_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in dataset_name)
            module_dir = os.path.dirname(os.path.abspath(__file__))
            models_dir = os.path.join(module_dir, 'models', dataset_name)
            output_dir = os.path.join(models_dir, 'autogluon_multimodal')
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure predictor
        predictor = MultiModalPredictor(
            label=label,
            path=output_dir,
        )
        
        # Train models
        predictor.fit(
            train_data=train_data,
            time_limit=time_limit,
        )
        
        # Prepare results
        result = {
            "status": "success",
            "model_path": output_dir,
            "label": label,
            "training_time": time_limit,
        }
        
        # Evaluate on test set if provided
        if test_csv_path:
            test_data = pd.read_csv(test_csv_path)
            
            if label in test_data.columns:
                # Evaluate
                eval_results = predictor.evaluate(test_data)
                result["test_evaluation"] = eval_results
                
                # Generate predictions
                predictions = predictor.predict(test_data.drop(columns=[label]))
                result["test_predictions"] = {
                    "sample_predictions": predictions.head(20).tolist(),
                    "num_predictions": len(predictions)
                }
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Multimodal training failed. Check your data and paths."
        }


@ensure_display_fields
async def train_specific_model(
    csv_path: str,
    target: str,
    model_type: str,
    hyperparameters: Optional[Dict[str, Any]] = None,
    time_limit: int = 300,
    output_dir: Optional[str] = None,
    test_csv_path: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Train a specific tabular model (not full AutoML).
    
    Available model types:
    - 'GBM' (LightGBM) - Gradient boosting, fast and accurate
    - 'CAT' (CatBoost) - Handles categorical features well
    - 'XGB' (XGBoost) - Powerful gradient boosting
    - 'RF' (Random Forest) - Ensemble of decision trees
    - 'XT' (Extra Trees) - Faster than Random Forest
    - 'KNN' (K-Nearest Neighbors) - Simple, interpretable
    - 'LR' (Linear/Logistic Regression) - Fast baseline
    - 'NN_TORCH' (Neural Network) - Deep learning model
    
    Args:
        csv_path: Path to training CSV file
        target: Name of the target column
        model_type: Model type to train (see list above)
        hyperparameters: Optional dict of model hyperparameters
        time_limit: Training time limit in seconds
        output_dir: Directory to save model
        test_csv_path: Optional test data for evaluation
        tool_context: ADK tool context
    
    Returns:
        Dictionary with model performance and details
    
    Example:
        train_specific_model(csv_path='data.csv', target='price', 
                           model_type='GBM', hyperparameters={'num_boost_round': 100})
    """
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed. Run: pip install autogluon.tabular"}
    
    try:
        # Load data
        train_data = TabularDataset(csv_path)
        train_data = _clean_dataframe(train_data)
        
        # Set output directory (organized by dataset)
        if output_dir is None:
            dataset_name = _get_original_dataset_name(csv_path, tool_context)
            dataset_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in dataset_name)
            module_dir = os.path.dirname(os.path.abspath(__file__))
            models_dir = os.path.join(module_dir, 'models', dataset_name)
            output_dir = os.path.join(models_dir, f'autogluon_{model_type.lower()}')
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure predictor
        predictor = TabularPredictor(label=target, path=output_dir)
        
        # Prepare hyperparameters dict
        if hyperparameters is None:
            hyperparameters = {}
        
        # Train single model
        predictor.fit(
            train_data=train_data,
            hyperparameters={model_type: hyperparameters},
            time_limit=time_limit,
        )
        
        # Get model info
        leaderboard = predictor.leaderboard(silent=True)
        
        result = {
            "status": "success",
            "model_path": output_dir,
            "model_type": model_type,
            "target": target,
            "problem_type": predictor.problem_type,
            "leaderboard": leaderboard.to_dict(),
            "hyperparameters_used": hyperparameters,
        }
        
        # Evaluate on test set if provided
        if test_csv_path:
            test_data = TabularDataset(test_csv_path)
            test_data = _clean_dataframe(test_data)
            
            if target in test_data.columns:
                eval_results = predictor.evaluate(test_data, silent=True)
                result["test_evaluation"] = eval_results
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to train {model_type} model. Check your data and hyperparameters."
        }


@ensure_display_fields
async def generate_features(
    csv_path: str,
    output_path: Optional[str] = None,
    enable_datetime: bool = True,
    enable_text: bool = True,
    enable_numeric: bool = True,
    enable_category: bool = True,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Generate additional features using AutoGluon's feature generators.
    
    Feature types:
    - Datetime features: year, month, day, hour, day_of_week, etc.
    - Text features: TF-IDF, bag of words, embeddings
    - Numeric features: normalization, binning, interactions
    - Category features: one-hot encoding, frequency encoding
    
    Args:
        csv_path: Path to input CSV
        output_path: Optional output path for enhanced CSV
        enable_datetime: Generate datetime features
        enable_text: Generate text features
        enable_numeric: Generate numeric transformations
        enable_category: Generate categorical encodings
        tool_context: ADK tool context
    
    Returns:
        Dictionary with feature generation statistics
    
    Example:
        generate_features('data.csv', enable_datetime=True, enable_text=True)
    """
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed"}
    
    try:
        from autogluon.features.generators import AutoMLPipelineFeatureGenerator
        
        # Load data
        df = pd.read_csv(csv_path)
        original_columns = list(df.columns)
        
        # Create feature generator
        feature_generator = AutoMLPipelineFeatureGenerator()
        
        # Fit and transform
        df_features = feature_generator.fit_transform(df)
        new_columns = list(df_features.columns)
        
        # Save enhanced data with original dataset name preserved
        if output_path is None:
            # Extract original dataset name (strips timestamp prefixes)
            clean_name = _extract_dataset_name(csv_path)
            
            # Build output path with timestamp + original name + _features
            timestamp = int(time.time())
            output_filename = f"{timestamp}_{clean_name}_features.csv"
            output_path = str(Path(csv_path).parent / output_filename)
        
        df_features.to_csv(output_path, index=False)
        
        result = {
            "status": "success",
            "input_file": csv_path,
            "output_file": output_path,
            "original_features": len(original_columns),
            "generated_features": len(new_columns),
            "new_feature_count": len(new_columns) - len(original_columns),
            "feature_names": new_columns,
        }
        
        # Save artifact
        if tool_context is not None:
            from google.genai import types
            buf = BytesIO()
            df_features.to_csv(buf, index=False)
            await tool_context.save_artifact(
                filename=Path(output_path).name,
                artifact=types.Part.from_bytes(
                    data=buf.getvalue(),
                    mime_type="text/csv"
                )
            )
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Feature generation failed."
        }


@ensure_display_fields
async def get_feature_metadata(
    csv_path: str,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Extract and analyze feature metadata from a dataset.
    
    Provides detailed information about:
    - Feature types (numeric, categorical, datetime, text)
    - Missing value statistics
    - Unique value counts
    - Data type recommendations
    - Memory usage
    
    Args:
        csv_path: Path to CSV file
        tool_context: ADK tool context
    
    Returns:
        Dictionary with comprehensive feature metadata
    
    Example:
        get_feature_metadata('data.csv')
    """
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed"}
    
    try:
        from autogluon.features import FeatureMetadata
        
        # Load data
        df = pd.read_csv(csv_path)
        
        # Create feature metadata
        feature_metadata = FeatureMetadata.from_df(df)
        
        result = {
            "status": "success",
            "file": csv_path,
            "total_features": len(df.columns),
            "feature_types": {
                "int": feature_metadata.get_features(valid_raw_types=['int']),
                "float": feature_metadata.get_features(valid_raw_types=['float']),
                "category": feature_metadata.get_features(valid_raw_types=['category']),
                "object": feature_metadata.get_features(valid_raw_types=['object']),
                "datetime": feature_metadata.get_features(valid_raw_types=['datetime']),
            },
            "type_counts": {
                "numeric": len(feature_metadata.get_features(required_special_types=[])),
                "categorical": len(df.select_dtypes(include=['object', 'category']).columns),
                "datetime": len(df.select_dtypes(include=['datetime']).columns),
            },
            "missing_values": df.isnull().sum().to_dict(),
            "unique_counts": {col: df[col].nunique() for col in df.columns},
            "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        }
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to extract feature metadata."
        }


@ensure_display_fields
async def customize_hyperparameter_search(
    csv_path: str,
    target: str,
    search_space: Dict[str, Any],
    num_trials: int = 10,
    searcher: str = "auto",
    output_dir: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Customize hyperparameter search for AutoGluon models.
    
    Search strategies:
    - 'auto': Automatic selection
    - 'random': Random search
    - 'bayes': Bayesian optimization
    - 'grid': Grid search (exhaustive)
    
    Args:
        csv_path: Path to training CSV
        target: Target column name
        search_space: Dictionary defining hyperparameter search space
        num_trials: Number of hyperparameter combinations to try
        searcher: Search strategy ('auto', 'random', 'bayes', 'grid')
        output_dir: Directory to save models
        tool_context: ADK tool context
    
    Returns:
        Dictionary with best hyperparameters and performance
    
    Example:
        search_space = {
            'GBM': {
                'num_boost_round': [100, 200, 300],
                'learning_rate': [0.01, 0.05, 0.1],
            }
        }
        customize_hyperparameter_search('data.csv', 'target', search_space, num_trials=5)
    """
    if not AUTOGLUON_AVAILABLE:
        return {"error": "AutoGluon not installed"}
    
    try:
        # Load data
        train_data = TabularDataset(csv_path)
        train_data = _clean_dataframe(train_data)
        
        # Set output directory (organized by dataset)
        if output_dir is None:
            dataset_name = _get_original_dataset_name(csv_path, tool_context)
            dataset_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in dataset_name)
            module_dir = os.path.dirname(os.path.abspath(__file__))
            models_dir = os.path.join(module_dir, 'models', dataset_name)
            output_dir = os.path.join(models_dir, 'autogluon_hpo')
        os.makedirs(output_dir, exist_ok=True)
        
        # Configure predictor
        predictor = TabularPredictor(label=target, path=output_dir)
        
        # Train with hyperparameter tuning
        predictor.fit(
            train_data=train_data,
            hyperparameters=search_space,
            num_bag_folds=0,  # Disable bagging for faster HPO
            num_bag_sets=1,
            num_stack_levels=0,  # Disable stacking for faster HPO
            hyperparameter_tune_kwargs={
                'num_trials': num_trials,
                'searcher': searcher,
                'scheduler': 'local',
            },
        )
        
        # Get results
        leaderboard = predictor.leaderboard(silent=True)
        best_model = predictor.model_best
        
        result = {
            "status": "success",
            "model_path": output_dir,
            "best_model": best_model,
            "num_trials": num_trials,
            "searcher": searcher,
            "search_space": search_space,
            "leaderboard": leaderboard.to_dict(),
        }
        
        return _json_safe(result)
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Hyperparameter search failed."
        }


@ensure_display_fields
async def list_available_models() -> dict:
    """List all AutoGluon models: GBM, XGB, CAT, RF, Neural Networks, Time Series models."""
    models = {
        "status": "success",
        "tabular_models": {
            "GBM": {
                "name": "LightGBM",
                "type": "Gradient Boosting",
                "description": "Fast, efficient gradient boosting. Best for most tabular data.",
                "pros": ["Fast training", "High accuracy", "Handles missing values"],
                "cons": ["May overfit on small data"],
            },
            "CAT": {
                "name": "CatBoost",
                "type": "Gradient Boosting",
                "description": "Excellent for categorical features, minimal preprocessing needed.",
                "pros": ["Handles categories natively", "Robust", "Low overfitting"],
                "cons": ["Slower than LightGBM"],
            },
            "XGB": {
                "name": "XGBoost",
                "type": "Gradient Boosting",
                "description": "Popular gradient boosting, very powerful.",
                "pros": ["High accuracy", "Well-tested", "GPU support"],
                "cons": ["Slower training"],
            },
            "RF": {
                "name": "Random Forest",
                "type": "Ensemble",
                "description": "Ensemble of decision trees, interpretable.",
                "pros": ["Robust", "Interpretable", "No hyperparameter tuning needed"],
                "cons": ["Large model size", "Slower inference"],
            },
            "XT": {
                "name": "Extra Trees",
                "type": "Ensemble",
                "description": "Faster variant of Random Forest.",
                "pros": ["Fast training", "Low overfitting"],
                "cons": ["Slightly lower accuracy than RF"],
            },
            "NN_TORCH": {
                "name": "Neural Network (PyTorch)",
                "type": "Deep Learning",
                "description": "Deep neural network, good for complex patterns.",
                "pros": ["Handles non-linear patterns", "Flexible"],
                "cons": ["Needs more data", "Slower training", "Less interpretable"],
            },
            "LR": {
                "name": "Linear/Logistic Regression",
                "type": "Linear Model",
                "description": "Simple, fast baseline model.",
                "pros": ["Very fast", "Interpretable", "Low memory"],
                "cons": ["Low accuracy for complex data"],
            },
            "KNN": {
                "name": "K-Nearest Neighbors",
                "type": "Instance-based",
                "description": "Simple distance-based model.",
                "pros": ["Simple", "No training needed"],
                "cons": ["Slow inference", "Memory intensive"],
            },
        },
        "timeseries_models": {
            "Chronos-Bolt": "Fast pretrained transformer, no GPU needed (bolt_tiny/small/base)",
            "Chronos": "Original pretrained transformer (tiny/mini/small/base/large)",
            "DeepAR": "Autoregressive RNN for probabilistic forecasting",
            "TemporalFusionTransformer": "Transformer with LSTM for multi-horizon forecasting",
            "PatchTST": "Transformer that segments time series into patches",
            "AutoARIMA": "Automatic ARIMA model selection",
            "AutoETS": "Automatic exponential smoothing",
            "Theta": "Theta forecasting method",
            "RecursiveTabular": "Tabular model with recursive forecasting",
            "DirectTabular": "Tabular model for direct multi-step forecasting",
        },
        "multimodal_models": {
            "Transformer": "Pretrained transformers for text/image/tabular fusion",
            "Fusion": "Late fusion of multiple modalities",
        },
    }
    
    return models


# Tool metadata for ADK integration
__all__ = [
    "auto_clean_data",
    "autogluon_automl",
    "autogluon_predict",
    "autogluon_feature_importance",
    "autogluon_timeseries",
    "autogluon_multimodal",
    "train_specific_model",
    "generate_features",
    "get_feature_metadata",
    "customize_hyperparameter_search",
    "list_available_models",
]

