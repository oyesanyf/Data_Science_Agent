"""
Chunk-aware AutoGluon tools that automatically handle large files.
These wrappers detect large files and process them in chunks.
"""

from typing import Optional, Dict, Any
import numpy as np
from google.adk.tools import ToolContext
from data_science.autogluon_tools import autogluon_automl, autogluon_timeseries
from data_science.chunking_utils import auto_chunk_if_needed, get_safe_csv_reference
from .ds_tools import ensure_display_fields


@ensure_display_fields
async def smart_autogluon_automl(
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
    """
    Chunk-aware AutoML. Automatically splits large files and detects target variables.
    
    Args:
        csv_path: Path to CSV file (auto-detects most recent if empty)
        target: Target column name (auto-detects if empty)
        task_type: 'classification', 'regression', or 'auto'
        time_limit: Training time limit in seconds
        presets: 'best_quality', 'high_quality', 'medium_quality', 'fast_training'
        output_dir: Where to save trained models
        test_csv_path: Optional test dataset path
        eval_metric: Evaluation metric
        tool_context: Tool context from ADK
    
    Returns:
        Training results with model performance
    """
    #  ENHANCED: Auto-detect most recent CSV if not provided
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
    
    #  ENHANCED: Auto-detect target variable if not provided
    if not target:
        import pandas as pd
        df = pd.read_csv(csv_path)
        
        # Smart target detection logic
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        # Priority order for target detection
        target_candidates = []
        
        # 1. Look for common target names
        common_targets = ['target', 'label', 'y', 'class', 'category', 'outcome', 'result', 'score', 'rating', 'grade']
        for col in df.columns:
            if any(term in col.lower() for term in common_targets):
                target_candidates.append(col)
        
        # 2. If no common names, use last column (often target)
        if not target_candidates and len(df.columns) > 1:
            target_candidates.append(df.columns[-1])
        
        # 3. If still no target, use first numeric column for regression
        if not target_candidates and numeric_cols:
            target_candidates.append(numeric_cols[0])
        
        if target_candidates:
            target = target_candidates[0]
            print(f" Auto-detected target: {target}")
        else:
            return {
                "error": "Could not auto-detect target variable",
                "available_columns": list(df.columns),
                "message": "Please specify target parameter"
            }
    
    # Check if file needs chunking
    file_info = get_safe_csv_reference(csv_path)
    
    if file_info["needs_chunking"]:
        # For large files, use sampling strategy
        import pandas as pd
        
        print(f"[WARNING] Large file detected: {csv_path}")
        print(f" Using sampling strategy for efficient training...")
        
        # Read and sample large file
        df = pd.read_csv(csv_path)
        
        # Smart sampling: keep class balance for classification
        if task_type == "classification" or task_type == "auto":
            # Sample up to 100k rows, stratified by target
            sample_size = min(100000, len(df))
            try:
                df_sample = df.groupby(target, group_keys=False).apply(
                    lambda x: x.sample(frac=sample_size/len(df), random_state=42)
                )
            except Exception:
                df_sample = df.sample(n=sample_size, random_state=42)
        else:
            # Simple random sampling for regression
            sample_size = min(100000, len(df))
            df_sample = df.sample(n=sample_size, random_state=42)
        
        # Save sampled data
        from pathlib import Path
        sample_path = Path(csv_path).parent / f"sample_{Path(csv_path).name}"
        df_sample.to_csv(sample_path, index=False)
        
        print(f"[OK] Created training sample: {len(df_sample):,} rows from {len(df):,}")
        print(f" Sample saved to: {sample_path}")
        
        # Train on sample
        result = await autogluon_automl(
            csv_path=str(sample_path),
            target=target,
            task_type=task_type,
            time_limit=time_limit,
            presets=presets,
            output_dir=output_dir,
            test_csv_path=test_csv_path,
            eval_metric=eval_metric,
            tool_context=tool_context
        )
        
        result["note"] = f"Trained on {len(df_sample):,} sampled rows from {len(df):,} total rows"
        return result
    
    else:
        # File is small enough, process normally
        return await autogluon_automl(
            csv_path=csv_path,
            target=target,
            task_type=task_type,
            time_limit=time_limit,
            presets=presets,
            output_dir=output_dir,
            test_csv_path=test_csv_path,
            eval_metric=eval_metric,
            tool_context=tool_context
        )


@ensure_display_fields
async def smart_autogluon_timeseries(
    csv_path: str,
    target: str,
    time_column: str,
    id_column: Optional[str] = None,
    prediction_length: int = 24,
    freq: Optional[str] = None,
    time_limit: int = 600,
    presets: str = "medium_quality",
    output_dir: Optional[str] = None,
    eval_metric: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Chunk-aware time series forecasting. Handles large time series datasets.
    
    Args:
        csv_path: Path to CSV with time series data
        target: Target column to forecast
        time_column: Timestamp column name
        id_column: Item ID column (for multiple time series)
        prediction_length: Forecast horizon
        freq: Time frequency ('H', 'D', 'W', 'M', etc.)
        time_limit: Training time limit in seconds
        presets: Model quality preset
        output_dir: Where to save models
        eval_metric: Evaluation metric
        tool_context: Tool context from ADK
    
    Returns:
        Forecasting results
    """
    # Check if file needs chunking
    file_info = get_safe_csv_reference(csv_path)
    
    if file_info["needs_chunking"]:
        print(f"[WARNING] Large time series file detected: {csv_path}")
        print(f" Processing in chunks...")
        
        # For time series, chunk by item_id if available
        import pandas as pd
        df = pd.read_csv(csv_path)
        
        if id_column and id_column in df.columns:
            # Sample subset of time series
            unique_ids = df[id_column].unique()
            sample_ids = unique_ids[:min(100, len(unique_ids))]
            df_sample = df[df[id_column].isin(sample_ids)]
            
            print(f"[OK] Sampled {len(sample_ids)} time series from {len(unique_ids)}")
        else:
            # Sample recent data
            df = df.sort_values(time_column)
            sample_size = min(50000, len(df))
            df_sample = df.tail(sample_size)
            
            print(f"[OK] Using most recent {len(df_sample):,} rows from {len(df):,}")
        
        # Save sample
        from pathlib import Path
        sample_path = Path(csv_path).parent / f"sample_{Path(csv_path).name}"
        df_sample.to_csv(sample_path, index=False)
        
        # Train on sample
        result = await autogluon_timeseries(
            csv_path=str(sample_path),
            target=target,
            time_column=time_column,
            id_column=id_column,
            prediction_length=prediction_length,
            freq=freq,
            time_limit=time_limit,
            presets=presets,
            output_dir=output_dir,
            eval_metric=eval_metric,
            tool_context=tool_context
        )
        
        result["note"] = f"Trained on sampled data from large dataset"
        return result
    
    else:
        # Process normally
        return await autogluon_timeseries(
            csv_path=csv_path,
            target=target,
            time_column=time_column,
            id_column=id_column,
            prediction_length=prediction_length,
            freq=freq,
            time_limit=time_limit,
            presets=presets,
            output_dir=output_dir,
            eval_metric=eval_metric,
            tool_context=tool_context
        )

