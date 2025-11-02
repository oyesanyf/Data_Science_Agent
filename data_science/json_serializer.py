"""Production-grade JSON serialization for data science tools."""
import json
import logging
from typing import Any
import numpy as np
import pandas as pd
from datetime import datetime, date

logger = logging.getLogger(__name__)

def to_json_safe(obj: Any, use_pydantic: bool = False) -> Any:
    """Convert any Python object to JSON-serializable format."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {str(k): to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_json_safe(item) for item in obj]
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records') if not obj.empty else []
    if isinstance(obj, pd.Series):
        return obj.to_dict() if not obj.empty else {}
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        val = float(obj)
        return None if (np.isnan(val) or np.isinf(val)) else val
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    return obj
