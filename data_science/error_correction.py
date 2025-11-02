"""
Runtime Error Auto-Correction System

Automatically fixes common errors at runtime:
- Typos in parameter names
- Similar column names
- Type conversions
- Missing values with smart defaults
- Path corrections
- Model name variations
"""

import os
import difflib
from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def find_closest_match(value: str, candidates: List[str], threshold: float = 0.6) -> Optional[str]:
    """Find the closest matching string from a list of candidates.
    
    Args:
        value: The value to match
        candidates: List of valid candidates
        threshold: Minimum similarity ratio (0-1)
    
    Returns:
        Closest match if similarity > threshold, else None
    """
    if not candidates:
        return None
    
    matches = difflib.get_close_matches(value, candidates, n=1, cutoff=threshold)
    return matches[0] if matches else None


def auto_correct_column_name(df: pd.DataFrame, column: str) -> Tuple[str, bool]:
    """Auto-correct column name if it doesn't exist in dataframe.
    
    Args:
        df: DataFrame
        column: Column name (potentially misspelled)
    
    Returns:
        Tuple of (corrected_name, was_corrected)
    """
    if column in df.columns:
        return column, False
    
    # Try case-insensitive match
    for col in df.columns:
        if col.lower() == column.lower():
            logger.info(f" Auto-corrected column name: '{column}' → '{col}' (case mismatch)")
            return col, True
    
    # Try fuzzy match
    closest = find_closest_match(column, list(df.columns), threshold=0.7)
    if closest:
        logger.info(f" Auto-corrected column name: '{column}' → '{closest}' (typo detected)")
        return closest, True
    
    return column, False


def auto_correct_file_path(path: str, search_dirs: Optional[List[str]] = None) -> Tuple[str, bool]:
    """Auto-correct file path if it doesn't exist.
    
    Args:
        path: File path (potentially wrong)
        search_dirs: Directories to search in
    
    Returns:
        Tuple of (corrected_path, was_corrected)
    """
    if os.path.exists(path):
        return path, False
    
    if not search_dirs:
        # Use proper folder structure
        try:
            from .large_data_config import UPLOAD_ROOT
            data_dir = str(UPLOAD_ROOT)
        except ImportError:
            data_dir = os.path.join(os.path.dirname(__file__), '.uploaded')
        
        search_dirs = [
            os.path.dirname(__file__),
            data_dir,
            os.path.join(os.path.dirname(__file__), '.export'),
            os.getcwd()
        ]
    
    filename = os.path.basename(path)
    
    # Search in common directories
    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
        
        candidate = os.path.join(directory, filename)
        if os.path.exists(candidate):
            logger.info(f" Auto-corrected file path: '{path}' → '{candidate}'")
            return candidate, True
        
        # Try finding similar files
        try:
            files = os.listdir(directory)
            closest = find_closest_match(filename, files, threshold=0.7)
            if closest:
                candidate = os.path.join(directory, closest)
                logger.info(f" Auto-corrected file path: '{path}' → '{candidate}' (similar file found)")
                return candidate, True
        except Exception:
            continue
    
    return path, False


def auto_correct_param_name(params: Dict[str, Any], param_name: str, valid_params: List[str]) -> Tuple[Optional[str], bool]:
    """Auto-correct parameter name if misspelled.
    
    Args:
        params: Parameter dictionary
        param_name: Parameter name to check
        valid_params: List of valid parameter names
    
    Returns:
        Tuple of (corrected_name, was_corrected)
    """
    if param_name in valid_params:
        return param_name, False
    
    # Try case-insensitive match
    for valid in valid_params:
        if valid.lower() == param_name.lower():
            logger.info(f" Auto-corrected parameter: '{param_name}' → '{valid}' (case mismatch)")
            return valid, True
    
    # Try fuzzy match
    closest = find_closest_match(param_name, valid_params, threshold=0.7)
    if closest:
        logger.info(f" Auto-corrected parameter: '{param_name}' → '{closest}' (typo detected)")
        return closest, True
    
    return None, False


def auto_convert_type(value: Any, target_type: type) -> Tuple[Any, bool]:
    """Auto-convert value to target type if possible.
    
    Args:
        value: Value to convert
        target_type: Target type
    
    Returns:
        Tuple of (converted_value, was_converted)
    """
    if isinstance(value, target_type):
        return value, False
    
    try:
        if target_type == bool:
            # Handle string booleans
            if isinstance(value, str):
                if value.lower() in ('true', '1', 'yes', 'y', 'on'):
                    logger.info(f" Auto-converted '{value}' to True")
                    return True, True
                elif value.lower() in ('false', '0', 'no', 'n', 'off'):
                    logger.info(f" Auto-converted '{value}' to False")
                    return False, True
        
        converted = target_type(value)
        logger.info(f" Auto-converted {type(value).__name__} to {target_type.__name__}: {value} → {converted}")
        return converted, True
    
    except Exception:
        return value, False


def auto_fix_common_errors(error: Exception, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Attempt to auto-fix common errors and provide suggestions.
    
    Args:
        error: The exception that occurred
        context: Context dict with function args, dataframe, etc.
    
    Returns:
        Tuple of (can_fix, suggestion_message)
    """
    error_msg = str(error).lower()
    
    # Column not found errors
    if 'not found' in error_msg or 'keyerror' in error_msg:
        df = context.get('df')
        if df is not None and isinstance(df, pd.DataFrame):
            # Extract column name from error
            import re
            match = re.search(r"['\"](.*?)['\"]", str(error))
            if match:
                bad_column = match.group(1)
                corrected, was_corrected = auto_correct_column_name(df, bad_column)
                if was_corrected:
                    return True, f"Did you mean column '{corrected}' instead of '{bad_column}'?"
    
    # Type errors
    if 'type' in error_msg and 'expected' in error_msg:
        return True, "Auto-converting data types..."
    
    # File not found errors
    if 'no such file' in error_msg or 'file not found' in error_msg:
        return True, "Searching for similar file paths..."
    
    return False, None


def with_error_correction(func: Callable) -> Callable:
    """Decorator that adds runtime error auto-correction to functions.
    
    Usage:
        @with_error_correction
        async def my_function(csv_path, target, ...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # First attempt - normal execution
            return await func(*args, **kwargs)
        
        except Exception as e:
            logger.info(f"[WARNING] Error detected: {type(e).__name__}: {str(e)[:100]}")
            
            # Attempt auto-correction
            corrected_kwargs = kwargs.copy()
            corrections_made = []
            
            # 1. Try to correct file paths
            if 'csv_path' in kwargs and kwargs['csv_path']:
                path, was_corrected = auto_correct_file_path(kwargs['csv_path'])
                if was_corrected:
                    corrected_kwargs['csv_path'] = path
                    corrections_made.append(f"File path: {kwargs['csv_path']} → {path}")
            
            # 2. Try to load dataframe and correct column names
            if 'target' in kwargs:
                try:
                    # Try to get dataframe context
                    from .ds_tools import _load_dataframe
                    df = await _load_dataframe(
                        corrected_kwargs.get('csv_path'),
                        corrected_kwargs.get('tool_context')
                    )
                    
                    target, was_corrected = auto_correct_column_name(df, kwargs['target'])
                    if was_corrected:
                        corrected_kwargs['target'] = target
                        corrections_made.append(f"Target column: {kwargs['target']} → {target}")
                    
                    # Correct other column-like parameters
                    for param in ['columns', 'sensitive_features', 'date_column', 'text_column']:
                        if param in kwargs and kwargs[param]:
                            if isinstance(kwargs[param], str):
                                corrected, was_corrected = auto_correct_column_name(df, kwargs[param])
                                if was_corrected:
                                    corrected_kwargs[param] = corrected
                                    corrections_made.append(f"{param}: {kwargs[param]} → {corrected}")
                            elif isinstance(kwargs[param], list):
                                new_list = []
                                for item in kwargs[param]:
                                    corrected, was_corrected = auto_correct_column_name(df, item)
                                    new_list.append(corrected)
                                    if was_corrected:
                                        corrections_made.append(f"{param} item: {item} → {corrected}")
                                corrected_kwargs[param] = new_list
                
                except Exception:
                    pass  # Couldn't load dataframe, continue with other corrections
            
            # 3. Correct model names (if estimator parameter)
            if 'estimator' in kwargs and kwargs['estimator']:
                from .ds_tools import _DEFAULT_CLASSIFIERS, _DEFAULT_REGRESSORS
                
                estimator = kwargs['estimator']
                all_models = list(_DEFAULT_CLASSIFIERS.keys()) + list(_DEFAULT_REGRESSORS.keys())
                
                # Try fuzzy match
                closest = find_closest_match(estimator, all_models, threshold=0.6)
                if closest:
                    corrected_kwargs['estimator'] = closest
                    corrections_made.append(f"Model name: {estimator} → {closest}")
            
            # If corrections were made, log them and retry
            if corrections_made:
                print(f"\n Auto-corrections applied:")
                for correction in corrections_made:
                    print(f"   • {correction}")
                print()
                
                try:
                    # Retry with corrected parameters
                    result = await func(*args, **corrected_kwargs)
                    print(f"[OK] Function succeeded after auto-correction!")
                    return result
                
                except Exception as retry_error:
                    # Still failed after corrections
                    print(f"[X] Auto-correction didn't fully resolve the issue.")
                    print(f"   Original error: {e}")
                    print(f"   After correction: {retry_error}")
                    raise retry_error
            
            else:
                # No corrections possible, re-raise original error
                raise e
    
    return wrapper


def smart_param_fill(func_params: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Intelligently fill missing parameters with smart defaults.
    
    Args:
        func_params: Parameters passed to function
        defaults: Default values to use
    
    Returns:
        Updated parameters dict
    """
    params = func_params.copy()
    filled = []
    
    for key, default_value in defaults.items():
        if key not in params or params[key] is None:
            params[key] = default_value
            filled.append(f"{key}={default_value}")
    
    if filled:
        logger.info(f" Auto-filled parameters: {', '.join(filled)}")
    
    return params


# Common default values for ML functions
ML_DEFAULTS = {
    'test_size': 0.2,
    'random_state': 42,
    'cv': 5,
    'n_estimators': 100,
    'max_depth': None,
    'max_iter': 1000,
    'time_limit': 60,
}


def print_correction_summary(corrections: List[str]):
    """Print a formatted summary of corrections made.
    
    Args:
        corrections: List of correction descriptions
    """
    if not corrections:
        return
    
    print("\n" + "="*60)
    print(" AUTO-CORRECTIONS APPLIED")
    print("="*60)
    for i, correction in enumerate(corrections, 1):
        print(f"{i}. {correction}")
    print("="*60 + "\n")


# Example usage and testing
if __name__ == "__main__":
    # Test column name correction
    df = pd.DataFrame({'Price': [1, 2, 3], 'Quantity': [4, 5, 6]})
    
    # Test with typo
    corrected, was_corrected = auto_correct_column_name(df, 'prise')  # typo
    print(f"'prise' → '{corrected}' (corrected: {was_corrected})")
    
    # Test with case mismatch
    corrected, was_corrected = auto_correct_column_name(df, 'price')
    print(f"'price' → '{corrected}' (corrected: {was_corrected})")
    
    # Test file path correction
    path, was_corrected = auto_correct_file_path('nonexistent.csv')
    print(f"File path corrected: {was_corrected}")

