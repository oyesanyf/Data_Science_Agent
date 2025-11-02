"""
Consensus anomaly detection with proper math.
"""
import numpy as np
import pandas as pd
from typing import Dict, Iterable, Set

def to_index_set(idx_like: Iterable[int]) -> Set[int]:
    """Convert index-like data to a set of integers."""
    return set(map(int, idx_like))

def consensus_from_methods(results: Dict[str, Iterable[int]], min_votes: int = 2) -> Set[int]:
    """
    Compute consensus anomalies from multiple detection methods.
    
    Args:
        results: Dict mapping method names to lists of anomaly indices
        min_votes: Minimum number of methods that must agree on an anomaly
        
    Returns:
        Set of row indices agreed upon by >= min_votes methods
    """
    votes = {}
    for method, idxs in results.items():
        for i in set(map(int, idxs)):
            votes[i] = votes.get(i, 0) + 1
    return {i for i, v in votes.items() if v >= min_votes}

def anomaly_summary(results: Dict[str, Iterable[int]], min_votes: int = 2) -> Dict[str, Any]:
    """Generate a comprehensive anomaly detection summary."""
    per_method_counts = {method: len(set(map(int, idxs))) for method, idxs in results.items()}
    consensus = consensus_from_methods(results, min_votes)
    
    return {
        "per_method_counts": per_method_counts,
        "consensus_count": len(consensus),
        "consensus_indices": sorted(list(consensus)),
        "min_votes": min_votes,
        "total_unique": len(set().union(*[set(map(int, idxs)) for idxs in results.values()]))
    }
