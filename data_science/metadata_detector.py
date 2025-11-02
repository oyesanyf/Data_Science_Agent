# -*- coding: utf-8 -*-
"""
 Generic Metadata Row Detector for Mixed-Format Datasets

Standalone tool for detecting and handling stacked metadata/header rows in datasets.
Common in scientific data (brain imaging, genomics, clinical trials, etc.)

Example use cases:
- brain_networks.csv: 3 rows of metadata before numeric data
- genomics data: sample annotations in first 2-5 rows
- clinical trials: protocol info stacked before patient data
- multi-table CSVs: section headers separating data blocks
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def detect_metadata_rows(
    csv_path: str = "",
    max_rows_to_check: int = 5,
    numeric_threshold_low: float = 0.5,
    numeric_threshold_high: float = 0.7,
) -> Dict[str, Any]:
    """
     Analyze a CSV file to detect stacked metadata/header rows.
    
    This tool scans the first N rows of a dataset to identify:
    - Empty separator rows (all NaN)
    - Metadata/annotation rows (mostly text before numeric data)
    - Duplicate header rows
    - The actual starting row of real data
    
    Strategy:
    1. Read first N rows of the CSV
    2. Analyze numeric content ratio for each row
    3. Compare consecutive rows to find transition from text → numeric
    4. Extract potential column names from metadata rows
    5. Return detailed analysis and recommendations
    
    Args:
        csv_path: Path to CSV file to analyze
        max_rows_to_check: Maximum number of initial rows to analyze (default: 5)
        numeric_threshold_low: Ratio below which row is considered non-numeric (default: 0.5)
        numeric_threshold_high: Ratio above which row is considered numeric data (default: 0.7)
    
    Returns:
        dict with:
            - status: "success" or "failed"
            - data_start_row: Index where actual data begins (0-based)
            - metadata_rows_found: Number of metadata rows detected
            - suggested_headers: Potential enhanced column names
            - should_rename_columns: Whether to apply suggested headers
            - analysis: Row-by-row breakdown
            - summary: Human-readable summary
            - recommendation: Action to take
    
    Examples:
        >>> # Detect metadata in brain networks dataset
        >>> result = detect_metadata_rows(csv_path="brain_networks.csv")
        >>> print(result["summary"])
        "Found 3 metadata row(s). Actual data starts at row 3. Suggested new column names extracted."
        
        >>> # Use with robust_auto_clean_file
        >>> detect_metadata_rows(csv_path="messy_dataset.csv")
        >>> # Then clean with: robust_auto_clean_file(csv_path="messy_dataset.csv")
    """
    # Import here to avoid circular dependency
    from .robust_auto_clean_file import detect_and_skip_metadata_rows
    import os
    
    # Convert empty string to None
    csv_path = csv_path if csv_path and csv_path.strip() else None
    
    if not csv_path:
        return {
            "status": "failed",
            "error": "No CSV file specified",
            "message": "Please provide csv_path parameter or upload a file first.",
        }
    
    if not os.path.exists(csv_path):
        return {
            "status": "failed",
            "error": "File not found",
            "message": f"The specified file does not exist: {csv_path}",
            "requested_path": csv_path,
        }
    
    try:
        # Read first N rows for analysis (lightweight)
        df_sample = pd.read_csv(csv_path, nrows=max_rows_to_check * 2, low_memory=False)
        
        # Run generic detector
        result = detect_and_skip_metadata_rows(
            df_sample,
            max_rows_to_check=max_rows_to_check,
            numeric_threshold_low=numeric_threshold_low,
            numeric_threshold_high=numeric_threshold_high,
        )
        
        # Add recommendation
        if result["metadata_rows_found"] > 0:
            recommendation = (
                f"[OK] ACTION REQUIRED: Skip first {result['metadata_rows_found']} row(s) when loading this CSV.\n"
                f"   Use: pd.read_csv('{csv_path}', skiprows={result['metadata_rows_found']})\n"
                f"   Or: robust_auto_clean_file(csv_path='{csv_path}')  # Auto-handles it!"
            )
        else:
            recommendation = "[OK] No metadata rows detected. Dataset appears clean - can load normally."
        
        result["recommendation"] = recommendation
        result["status"] = "success"
        result["file_analyzed"] = csv_path
        
        return result
        
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Analysis failed: {str(e)}",
            "file_analyzed": csv_path,
        }


def preview_metadata_structure(csv_path: str = "", rows: int = 10) -> Dict[str, Any]:
    """
     Preview the first N rows of a CSV to understand its structure.
    
    Useful for manually inspecting datasets with unusual formats before cleaning.
    
    Args:
        csv_path: Path to CSV file
        rows: Number of rows to preview (default: 10)
    
    Returns:
        dict with:
            - status: "success" or "failed"
            - preview_rows: First N rows as list of dicts
            - columns: Column names detected
            - shape: (rows, columns)
            - recommendation: What to do next
    """
    csv_path = csv_path if csv_path and csv_path.strip() else None
    
    if not csv_path:
        return {
            "status": "failed",
            "error": "No CSV file specified",
        }
    
    import os
    if not os.path.exists(csv_path):
        return {
            "status": "failed",
            "error": f"File not found: {csv_path}",
        }
    
    try:
        df = pd.read_csv(csv_path, nrows=rows, low_memory=False)
        
        # Convert to serializable format
        preview_data = []
        for idx, row in df.iterrows():
            row_dict = {"row_index": int(idx)}
            for col in df.columns:
                val = row[col]
                # Handle NaN, numpy types
                if pd.isna(val):
                    row_dict[str(col)] = None
                elif isinstance(val, (np.integer, np.floating)):
                    row_dict[str(col)] = float(val)
                else:
                    row_dict[str(col)] = str(val)
            preview_data.append(row_dict)
        
        # Analyze structure
        numeric_cols = len(df.select_dtypes(include=[np.number]).columns)
        object_cols = len(df.select_dtypes(include=['object']).columns)
        
        recommendation = (
            f" Structure: {numeric_cols} numeric, {object_cols} text columns.\n"
            "Next steps:\n"
            "1. Use detect_metadata_rows() to check for stacked headers\n"
            "2. Use robust_auto_clean_file() to clean the dataset\n"
            "3. Use head() and describe() to explore cleaned data"
        )
        
        return {
            "status": "success",
            "file_analyzed": csv_path,
            "preview_rows": preview_data,
            "columns": list(df.columns),
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "numeric_columns": numeric_cols,
            "text_columns": object_cols,
            "recommendation": recommendation,
        }
        
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Preview failed: {str(e)}",
            "file_analyzed": csv_path,
        }

