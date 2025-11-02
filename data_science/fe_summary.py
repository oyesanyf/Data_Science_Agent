"""
Feature engineering summary utilities.
"""
from typing import List, Dict

def feature_change_summary(before_cols: List[str], after_cols: List[str]) -> Dict[str, int]:
    """Compute feature engineering summary without negative counts."""
    before = set(before_cols)
    after = set(after_cols)
    added = sorted(list(after - before))
    dropped = sorted(list(before - after))
    
    return {
        "original": len(before_cols),
        "generated": len(added),       # never negative
        "dropped": len(dropped),
        "total": len(after_cols),
        "added_features": added,
        "dropped_features": dropped
    }
