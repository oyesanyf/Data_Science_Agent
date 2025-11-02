"""
Production-grade JSON serialization for data science tools.

Handles:
- pandas DataFrames and Series
- numpy arrays and scalar types
- NaN, Inf, datetime objects
- Nested dictionaries and lists
- Custom objects with __dict__

Uses Pydantic for robust, schema-aware serialization.
"""

import json
import logging
from typing import Any, Dict, List, Union
from datetime import datetime, date
import numpy as np
import pandas as pd

try:
    from pydantic import BaseModel, Field, ConfigDict
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    logging.warning("[JSON_SERIALIZER] Pydantic not available, using fallback serialization")

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC-BASED SERIALIZATION (ROBUST, PRODUCTION-READY)
# ============================================================================

if PYDANTIC_AVAILABLE:
    class DataScienceResult(BaseModel):
        """
        Generic Pydantic model for data science tool results.
        Automatically coerces complex types to JSON-serializable formats.
        """
        model_config = ConfigDict(
            arbitrary_types_allowed=True,  # Allow pandas/numpy types
            json_encoders={
                # Pandas types
                pd.DataFrame: lambda df: df.to_dict(orient='records') if not df.empty else [],
                pd.Series: lambda s: s.to_dict() if not s.empty else {},
                pd.Timestamp: lambda ts: ts.isoformat(),
                pd.Timedelta: lambda td: str(td),
                # Numpy types
                np.ndarray: lambda arr: arr.tolist(),
                np.integer: lambda x: int(x),
                np.floating: lambda x: float(x) if not (np.isnan(x) or np.isinf(x)) else None,
                np.bool_: lambda x: bool(x),
                np.generic: lambda x: x.item(),
                # Datetime types
                datetime: lambda dt: dt.isoformat(),
                date: lambda d: d.isoformat(),
                # Handle NaN/Inf
                float: lambda x: None if (np.isnan(x) or np.isinf(x)) else x,
            }
        )

        def to_json_safe(self) -> Dict[str, Any]:
            """Convert to JSON-safe dictionary."""
            return json.loads(self.model_dump_json())


def pydantic_serialize(obj: Any) -> Dict[str, Any]:
    """
    Serialize any object using Pydantic's robust type coercion.
    
    Args:
        obj: Any Python object (dict, DataFrame, numpy array, etc.)
    
    Returns:
        JSON-serializable dictionary
    
    Example:
        >>> df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        >>> result = {'data': df, 'status': 'success'}
        >>> safe_result = pydantic_serialize(result)
        >>> json.dumps(safe_result)  # Works!
    """
    if not PYDANTIC_AVAILABLE:
        return fallback_serialize(obj)
    
    try:
        # If it's already a dict, wrap it in a Pydantic model
        if isinstance(obj, dict):
            # Create a dynamic model with the dict's fields
            model = DataScienceResult.model_construct(**obj)
            return model.to_json_safe()
        else:
            # For non-dict objects, convert to dict first
            if hasattr(obj, '__dict__'):
                obj_dict = obj.__dict__
            else:
                obj_dict = {'value': obj}
            model = DataScienceResult.model_construct(**obj_dict)
            return model.to_json_safe()
    except Exception as e:
        logger.warning(f"[JSON_SERIALIZER] Pydantic serialization failed: {e}, using fallback")
        return fallback_serialize(obj)


# ============================================================================
# FALLBACK SERIALIZATION (SIMPLE, NO DEPENDENCIES)
# ============================================================================

def fallback_serialize(obj: Any) -> Any:
    """
    Fallback JSON serialization without Pydantic.
    Handles common data science types manually.
    
    Args:
        obj: Any Python object
    
    Returns:
        JSON-serializable version of obj
    """
    # Handle None
    if obj is None:
        return None
    
    # Handle dictionaries recursively
    if isinstance(obj, dict):
        return {_safe_key(k): fallback_serialize(v) for k, v in obj.items()}
    
    # Handle lists, tuples, sets
    if isinstance(obj, (list, tuple, set)):
        return [fallback_serialize(item) for item in obj]
    
    # Handle pandas DataFrame
    if isinstance(obj, pd.DataFrame):
        if obj.empty:
            return []
        try:
            return obj.to_dict(orient='records')
        except Exception as e:
            logger.warning(f"[JSON_SERIALIZER] DataFrame conversion failed: {e}")
            return {"error": f"DataFrame conversion failed: {str(e)}"}
    
    # Handle pandas Series
    if isinstance(obj, pd.Series):
        if obj.empty:
            return {}
        try:
            return obj.to_dict()
        except Exception as e:
            logger.warning(f"[JSON_SERIALIZER] Series conversion failed: {e}")
            return {"error": f"Series conversion failed: {str(e)}"}
    
    # Handle pandas Timestamp
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    
    # Handle pandas Timedelta
    if isinstance(obj, pd.Timedelta):
        return str(obj)
    
    # Handle numpy arrays
    if isinstance(obj, np.ndarray):
        try:
            return obj.tolist()
        except Exception as e:
            logger.warning(f"[JSON_SERIALIZER] Array conversion failed: {e}")
            return {"error": f"Array conversion failed: {str(e)}"}
    
    # Handle numpy scalar types
    if isinstance(obj, np.integer):
        return int(obj)
    
    if isinstance(obj, np.floating):
        val = float(obj)
        # Convert NaN and Inf to None
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    
    if isinstance(obj, np.bool_):
        return bool(obj)
    
    if isinstance(obj, np.generic):
        return obj.item()
    
    # Handle datetime objects
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    
    # Handle Python floats with NaN/Inf
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    
    # Handle objects with __dict__
    if hasattr(obj, '__dict__'):
        return fallback_serialize(obj.__dict__)
    
    # Return as-is for primitive types (str, int, bool, etc.)
    return obj


def _safe_key(key: Any) -> str:
    """Convert any key to a safe string key for JSON."""
    if isinstance(key, str):
        return key
    if isinstance(key, (int, float, bool)):
        return str(key)
    if isinstance(key, (datetime, date)):
        return key.isoformat()
    return str(key)


# ============================================================================
# PUBLIC API
# ============================================================================

def to_json_safe(obj: Any, use_pydantic: bool = True) -> Dict[str, Any]:
    """
    Convert any Python object to a JSON-serializable dictionary.
    
    This is the main entry point for serialization. It automatically:
    - Converts pandas DataFrames to lists of dicts
    - Converts pandas Series to dicts
    - Handles numpy arrays and scalar types
    - Converts NaN/Inf to None
    - Handles datetime objects
    - Recursively processes nested structures
    
    Args:
        obj: Any Python object to serialize
        use_pydantic: If True and Pydantic is available, use Pydantic serialization
                      If False or Pydantic unavailable, use fallback serialization
    
    Returns:
        JSON-serializable dictionary
    
    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'a': [1, np.nan, 3], 'b': [4, 5, 6]})
        >>> result = {'data': df, 'status': 'success', 'timestamp': datetime.now()}
        >>> safe_result = to_json_safe(result)
        >>> json.dumps(safe_result)  # Works perfectly!
    """
    if use_pydantic and PYDANTIC_AVAILABLE:
        return pydantic_serialize(obj)
    else:
        return fallback_serialize(obj)


def json_safe_decorator(func):
    """
    Decorator to automatically serialize function return values.
    
    Usage:
        @json_safe_decorator
        def my_tool(...) -> dict:
            df = pd.DataFrame(...)
            return {'data': df, 'status': 'success'}
    """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return to_json_safe(result)
    return wrapper


# ============================================================================
# TESTING AND VALIDATION
# ============================================================================

def test_serialization():
    """Test serialization with various data types."""
    import numpy as np
    import pandas as pd
    from datetime import datetime
    
    # Create test data
    df = pd.DataFrame({
        'int_col': [1, 2, 3],
        'float_col': [1.1, np.nan, 3.3],
        'str_col': ['a', 'b', 'c'],
        'datetime_col': pd.date_range('2024-01-01', periods=3)
    })
    
    test_obj = {
        'dataframe': df,
        'series': pd.Series([1, 2, 3], name='test'),
        'numpy_array': np.array([1, 2, 3]),
        'numpy_scalar': np.int64(42),
        'nan_value': np.nan,
        'inf_value': np.inf,
        'datetime': datetime.now(),
        'nested': {
            'inner_df': df.head(2),
            'inner_list': [1, 2, {'key': df}]
        }
    }
    
    # Test serialization
    print("[TEST] Testing Pydantic serialization...")
    result_pydantic = to_json_safe(test_obj, use_pydantic=True)
    print(f"[OK] Pydantic result keys: {list(result_pydantic.keys())}")
    
    print("\n[TEST] Testing fallback serialization...")
    result_fallback = to_json_safe(test_obj, use_pydantic=False)
    print(f"[OK] Fallback result keys: {list(result_fallback.keys())}")
    
    # Verify JSON serialization works
    print("\n[TEST] Testing JSON serialization...")
    json_str = json.dumps(result_fallback, indent=2)
    print(f"[OK] JSON serialization successful ({len(json_str)} bytes)")
    
    return result_fallback


if __name__ == "__main__":
    print("=" * 80)
    print("JSON SERIALIZER TEST")
    print("=" * 80)
    test_serialization()

