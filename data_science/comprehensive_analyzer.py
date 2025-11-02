"""
Comprehensive data analysis tool that handles missing values and file issues.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import os

logger = logging.getLogger(__name__)

def analyze_dataset_comprehensive(
    file_path: str,
    include_cleaning: str = "yes",
    target_column: str = "",
    tool_context: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Comprehensive dataset analysis with robust error handling.
    
    Args:
        file_path: Path to the dataset file
        include_cleaning: Whether to include cleaning suggestions
        target_column: Target column for analysis
        tool_context: Tool context for artifact management
        
    Returns:
        Comprehensive analysis results
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "suggestions": [
                    "Check if the file path is correct",
                    "Verify the file exists in the workspace",
                    "Try re-uploading the file"
                ]
            }
        
        # Try multiple encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        df = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            return {
                "success": False,
                "error": "Could not read file with any supported encoding",
                "suggestions": [
                    "Check if the file is a valid CSV",
                    "Try saving the file with UTF-8 encoding",
                    "Verify the file is not corrupted"
                ]
            }
        
        # Basic dataset info
        dataset_info = {
            "file_path": file_path,
            "encoding": used_encoding,
            "shape": df.shape,
            "rows": len(df),
            "columns": len(df.columns),
            "memory_usage": df.memory_usage(deep=True).sum()
        }
        
        # Column analysis
        column_analysis = {}
        missing_summary = {}
        
        for col in df.columns:
            col_info = {
                "data_type": str(df[col].dtype),
                "non_null_count": df[col].count(),
                "null_count": df[col].isnull().sum(),
                "null_percentage": round((df[col].isnull().sum() / len(df)) * 100, 2),
                "unique_count": df[col].nunique(),
                "duplicate_count": len(df) - df[col].nunique()
            }
            
            # Add statistics for numeric columns
            if df[col].dtype in ['int64', 'float64']:
                col_info.update({
                    "mean": df[col].mean(),
                    "std": df[col].std(),
                    "min": df[col].min(),
                    "max": df[col].max(),
                    "median": df[col].median()
                })
            
            column_analysis[col] = col_info
            
            # Track missing values
            if col_info["null_count"] > 0:
                missing_summary[col] = {
                    "missing_count": col_info["null_count"],
                    "missing_percentage": col_info["null_percentage"],
                    "is_highly_missing": col_info["null_percentage"] > 50,
                    "is_completely_missing": col_info["null_percentage"] == 100
                }
        
        # Identify problematic columns
        problematic_columns = []
        for col, missing_info in missing_summary.items():
            if missing_info["is_completely_missing"]:
                problematic_columns.append({
                    "column": col,
                    "issue": "completely_missing",
                    "suggestion": "Drop this column"
                })
            elif missing_info["is_highly_missing"]:
                problematic_columns.append({
                    "column": col,
                    "issue": "highly_missing",
                    "suggestion": "Consider dropping or imputing"
                })
        
        # Data quality score
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        data_quality_score = round(((total_cells - missing_cells) / total_cells) * 100, 2)
        
        # Cleaning recommendations
        cleaning_recommendations = []
        
        if problematic_columns:
            cleaning_recommendations.append("Remove problematic columns with high missing values")
        
        if missing_cells > 0:
            cleaning_recommendations.append("Apply imputation for remaining missing values")
        
        if data_quality_score < 80:
            cleaning_recommendations.append("Dataset has significant data quality issues")
        
        # Target column analysis
        target_analysis = {}
        if target_column and target_column in df.columns:
            target_col = df[target_column]
            target_analysis = {
                "exists": True,
                "data_type": str(target_col.dtype),
                "missing_count": target_col.isnull().sum(),
                "missing_percentage": round((target_col.isnull().sum() / len(df)) * 100, 2),
                "unique_values": target_col.nunique(),
                "is_numeric": target_col.dtype in ['int64', 'float64'],
                "is_categorical": target_col.dtype == 'object' or target_col.nunique() < 20
            }
        elif target_column:
            target_analysis = {
                "exists": False,
                "error": f"Target column '{target_column}' not found in dataset",
                "available_columns": list(df.columns)
            }
        
        # Create summary
        summary = {
            "dataset_ready": data_quality_score > 80 and len(problematic_columns) == 0,
            "data_quality_score": data_quality_score,
            "critical_issues": len([p for p in problematic_columns if p["issue"] == "completely_missing"]),
            "warnings": len([p for p in problematic_columns if p["issue"] == "highly_missing"]),
            "recommendations": cleaning_recommendations
        }
        
        # Save analysis results if tool_context provided
        artifacts = []
        if tool_context:
            try:
                # Save detailed analysis
                analysis_file = f"dataset_analysis_{int(time.time())}.json"
                import json
                import time
                
                analysis_data = {
                    "dataset_info": dataset_info,
                    "column_analysis": column_analysis,
                    "missing_summary": missing_summary,
                    "problematic_columns": problematic_columns,
                    "target_analysis": target_analysis,
                    "summary": summary
                }
                
                await tool_context.save_artifact(
                    filename=analysis_file,
                    artifact=types.Part.from_bytes(
                        data=json.dumps(analysis_data, indent=2, default=str).encode('utf-8'),
                        mime_type="application/json"
                    )
                )
                artifacts.append(analysis_file)
                
            except Exception as e:
                logger.warning(f"Could not save analysis artifact: {e}")
        
        return {
            "success": True,
            "dataset_info": dataset_info,
            "column_analysis": column_analysis,
            "missing_summary": missing_summary,
            "problematic_columns": problematic_columns,
            "target_analysis": target_analysis,
            "summary": summary,
            "artifacts": artifacts
        }
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}",
            "suggestions": [
                "Check if the file is a valid CSV",
                "Verify the file encoding",
                "Try cleaning the data manually first"
            ]
        }
