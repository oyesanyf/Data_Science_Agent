"""
Comprehensive data validation and cleaning for robust data processing.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates and cleans datasets with comprehensive error handling."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        
    def validate_file_exists(self, file_path: str) -> Tuple[bool, str]:
        """Validate that file exists and is accessible."""
        try:
            path = Path(file_path)
            if not path.exists():
                return False, f"File not found: {file_path}"
            if not path.is_file():
                return False, f"Path is not a file: {file_path}"
            if path.stat().st_size == 0:
                return False, f"File is empty: {file_path}"
            return True, "File exists and is accessible"
        except Exception as e:
            return False, f"Error accessing file: {str(e)}"
    
    def detect_encoding(self, file_path: str) -> Tuple[str, bool]:
        """Detect file encoding."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)  # Read first 1KB
                return encoding, True
            except UnicodeDecodeError:
                continue
        
        return 'utf-8', False  # Default fallback
    
    def validate_csv_structure(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate CSV structure and detect issues."""
        try:
            # Check file exists
            exists, msg = self.validate_file_exists(file_path)
            if not exists:
                return False, {"error": msg, "type": "file_not_found"}
            
            # Detect encoding
            encoding, encoding_ok = self.detect_encoding(file_path)
            if not encoding_ok:
                return False, {"error": "Could not detect file encoding", "type": "encoding_error"}
            
            # Try to read CSV
            try:
                df = pd.read_csv(file_path, encoding=encoding, nrows=1000)  # Read first 1000 rows
            except Exception as e:
                return False, {"error": f"CSV parsing error: {str(e)}", "type": "csv_parse_error"}
            
            # Validate structure
            if df.empty:
                return False, {"error": "CSV file is empty", "type": "empty_file"}
            
            if len(df.columns) == 0:
                return False, {"error": "CSV has no columns", "type": "no_columns"}
            
            # Check for completely empty rows
            empty_rows = df.isnull().all(axis=1).sum()
            if empty_rows > len(df) * 0.5:  # More than 50% empty rows
                return False, {"error": f"Too many empty rows: {empty_rows}/{len(df)}", "type": "too_many_empty_rows"}
            
            return True, {
                "rows": len(df),
                "columns": len(df.columns),
                "encoding": encoding,
                "empty_rows": empty_rows,
                "column_names": list(df.columns)
            }
            
        except Exception as e:
            return False, {"error": f"Validation error: {str(e)}", "type": "validation_error"}
    
    def analyze_missing_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze missing values in the dataset."""
        missing_analysis = {}
        
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            missing_pct = (missing_count / len(df)) * 100
            
            missing_analysis[col] = {
                "missing_count": int(missing_count),
                "missing_percentage": round(missing_pct, 2),
                "data_type": str(df[col].dtype),
                "unique_values": df[col].nunique(),
                "is_highly_missing": missing_pct > 50,
                "is_completely_missing": missing_pct == 100
            }
        
        return missing_analysis
    
    def suggest_cleaning_strategy(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Suggest cleaning strategy based on data analysis."""
        missing_analysis = self.analyze_missing_values(df)
        
        suggestions = {
            "drop_columns": [],
            "impute_columns": [],
            "drop_rows": False,
            "strategies": {}
        }
        
        for col, analysis in missing_analysis.items():
            if analysis["is_completely_missing"]:
                suggestions["drop_columns"].append(col)
            elif analysis["is_highly_missing"]:
                suggestions["drop_columns"].append(col)
            elif analysis["missing_percentage"] > 0:
                suggestions["impute_columns"].append(col)
                
                # Suggest imputation strategy
                if analysis["data_type"] in ["object", "category"]:
                    suggestions["strategies"][col] = "mode_imputation"
                else:
                    suggestions["strategies"][col] = "mean_imputation"
        
        return suggestions
    
    def clean_dataset(self, file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Clean dataset with comprehensive error handling."""
        try:
            # Validate file first
            is_valid, validation_result = self.validate_csv_structure(file_path)
            if not is_valid:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "error_type": validation_result["type"]
                }
            
            # Read the full dataset
            encoding = validation_result["encoding"]
            df = pd.read_csv(file_path, encoding=encoding)
            
            # Analyze missing values
            missing_analysis = self.analyze_missing_values(df)
            
            # Get cleaning suggestions
            suggestions = self.suggest_cleaning_strategy(df)
            
            # Apply cleaning
            original_shape = df.shape
            cleaning_log = []
            
            # Drop completely missing columns
            if suggestions["drop_columns"]:
                df = df.drop(columns=suggestions["drop_columns"])
                cleaning_log.append(f"Dropped columns: {suggestions['drop_columns']}")
            
            # Impute missing values
            for col in suggestions["impute_columns"]:
                if col in df.columns:
                    strategy = suggestions["strategies"].get(col, "mean_imputation")
                    
                    if strategy == "mode_imputation":
                        mode_value = df[col].mode()
                        if not mode_value.empty:
                            df[col] = df[col].fillna(mode_value[0])
                            cleaning_log.append(f"Imputed {col} with mode: {mode_value[0]}")
                        else:
                            df[col] = df[col].fillna("Unknown")
                            cleaning_log.append(f"Imputed {col} with 'Unknown'")
                    else:  # mean_imputation
                        if df[col].dtype in ['int64', 'float64']:
                            mean_value = df[col].mean()
                            df[col] = df[col].fillna(mean_value)
                            cleaning_log.append(f"Imputed {col} with mean: {mean_value:.2f}")
                        else:
                            # For non-numeric, use mode or 'Unknown'
                            mode_value = df[col].mode()
                            if not mode_value.empty:
                                df[col] = df[col].fillna(mode_value[0])
                                cleaning_log.append(f"Imputed {col} with mode: {mode_value[0]}")
                            else:
                                df[col] = df[col].fillna("Unknown")
                                cleaning_log.append(f"Imputed {col} with 'Unknown'")
            
            # Drop rows that are still completely empty
            df = df.dropna(how='all')
            
            # Reset index
            df = df.reset_index(drop=True)
            
            # Save cleaned dataset
            if output_path is None:
                output_path = file_path.replace('.csv', '_cleaned.csv')
            
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            return {
                "success": True,
                "original_shape": original_shape,
                "cleaned_shape": df.shape,
                "output_path": output_path,
                "cleaning_log": cleaning_log,
                "missing_analysis": missing_analysis,
                "suggestions_applied": suggestions
            }
            
        except Exception as e:
            logger.error(f"Dataset cleaning failed: {e}")
            return {
                "success": False,
                "error": f"Cleaning failed: {str(e)}",
                "error_type": "cleaning_error"
            }

def validate_and_clean_file(file_path: str) -> Dict[str, Any]:
    """Convenience function to validate and clean a file."""
    validator = DataValidator()
    return validator.clean_dataset(file_path)
