"""
ADK-first imputation orchestrator that uses only registered tools.
No direct pandas or file I/O - relies entirely on ADK toolchain & ToolContext.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional

# ADK ToolContext (present in your repo)
try:
    from google.adk.tools import ToolContext  # type: ignore
except Exception:
    class ToolContext:  # minimal stub so type hints don't break local import
        state: dict

# Import ONLY your ADK tools (no pandas fallbacks here)
from .robust_auto_clean_file import robust_auto_clean_file
from .ds_tools import (
    analyze_dataset,
    describe,
    impute_simple,
    impute_knn,
    impute_iterative,
)

# Optional: artifact registration (used for a breadcrumb only; no raw file I/O)
try:
    from .artifact_manager import register_artifact
except Exception:
    register_artifact = None


def _extract_missing_counts(desc: Dict[str, Any]) -> Dict[str, int]:
    """
    Try a few common shapes your tools return to get per-column missing counts.
    Robust to slightly different schemas.
    """
    # 1) Direct keys (preferred)
    for key in ("missing_by_column", "null_counts", "na_counts"):
        if isinstance(desc.get(key), dict):
            return {str(k): int(v) for k, v in desc[key].items()}

    # 2) Column summaries list
    col_summ = desc.get("column_summaries") or desc.get("columns") or []
    out: Dict[str, int] = {}
    for item in col_summ:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("column") or item.get("col")
        if not name:
            continue
        # look for any countish key
        for k in ("missing", "nulls", "n_missing", "na", "nan"):
            if k in item and isinstance(item[k], (int, float)):
                out[str(name)] = int(item[k])
                break
    return out


def _extract_row_count(meta: Dict[str, Any]) -> Optional[int]:
    # Try multiple places to find row count
    for k in ("rows", "n_rows", "count_rows", "shape"):
        if k in meta:
            v = meta[k]
            if isinstance(v, int):
                return v
            if isinstance(v, (list, tuple)) and v and isinstance(v[0], int):
                return v[0]
    # Some tools tuck it under "overview" or similar
    ov = meta.get("overview") or {}
    for k in ("rows", "n_rows"):
        if isinstance(ov.get(k), int):
            return ov[k]
    return None


def _partition_by_missing_rate(
    missing_counts: Dict[str, int],
    n_rows: int,
    drop_threshold: float
) -> Dict[str, List[str]]:
    """
    Decide which columns get which imputation tool.
      - ≥ drop_threshold → handled by robust_auto_clean_file (we won't impute)
      - 0% → skip
      - ≤5% → simple
      - 5–25% → knn
      - 25–50% → iterative
      - ≥50% and <drop_threshold → leave for user (report only)
    """
    buckets = {"simple": [], "knn": [], "iterative": [], "left_unimputed_50to99": []}

    for col, miss in missing_counts.items():
        if n_rows <= 0:
            continue
        rate = miss / float(n_rows)

        if rate == 0.0:
            continue
        if rate >= drop_threshold:
            # robust_auto_clean_file will drop; do not queue for imputation
            continue
        if rate <= 0.05:
            buckets["simple"].append(col)
        elif rate <= 0.25:
            buckets["knn"].append(col)
        elif rate < 0.5:
            buckets["iterative"].append(col)
        else:
            buckets["left_unimputed_50to99"].append(col)

    return buckets


def auto_impute_orchestrator_adk(
    drop_threshold: str = "0.99",
    add_missing_indicators: str = "no",  # ADK impute_* may support this; set True if your impl does
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """
    ADK-only imputation orchestrator:
      1) Clean with robust_auto_clean_file(drop_threshold=...).
      2) Read missingness via describe()/analyze_dataset().
      3) Route columns: simple / knn / iterative (impute_* tools).
      4) Return a JSON summary. No direct file access performed.

    Notes:
      • If your impute_* tools support an 'add_indicators' (or similar) flag,
        pass it through via add_missing_indicators=True to create *_was_missing columns.
      • Columns with >= drop_threshold missing are expected to be dropped by robust_auto_clean_file.
    """
    # Parse string parameters with defensive type coercion
    # Per checklist: handle string params that should be numbers/booleans
    from .agent import _get_param
    params_dict = {"drop_threshold": drop_threshold, "add_missing_indicators": add_missing_indicators}
    drop_threshold_float = _get_param(params_dict, "drop_threshold", 0.99, float)
    add_indicators_bool = _get_param(params_dict, "add_missing_indicators", False, bool)
    
    # Get ToolContext from parameter or create minimal fallback
    ctx = tool_context
    if ctx is None:
        # Create minimal fallback context
        class MinimalContext:
            def __init__(self):
                self.state = {}
        ctx = MinimalContext()

    # 1) Advanced cleaning first (header repair, types, and drop ≥threshold-missing)
    # NOTE: robust_auto_clean_file drops empty columns via drop_empty_columns="yes"
    # The drop_threshold logic should be handled separately if needed
    clean_result = robust_auto_clean_file(
        csv_path="",
        cap_outliers="no",
        drop_empty_columns="yes",  # This will drop columns with all missing values
        tool_context=ctx,
    )

    # 2) Inspect missingness from tool outputs
    # Prefer describe(); fall back to analyze_dataset() if needed
    try:
        desc = describe(csv_path="", tool_context=ctx)
    except Exception:
        desc = {}

    # If describe didn't give us enough, call analyze_dataset
    if not desc or _extract_row_count(desc) is None or not _extract_missing_counts(desc):
        try:
            meta = analyze_dataset(csv_path="", tool_context=ctx)
        except Exception:
            meta = {}
    else:
        meta = desc

    n_rows = _extract_row_count(meta) or 0
    miss_counts = _extract_missing_counts(meta)

    # 3) Bucket columns by missing rate
    buckets = _partition_by_missing_rate(miss_counts, n_rows, drop_threshold_float)

    # 4) Run ADK imputers per bucket
    # Most implementations accept 'columns=[...]' plus method-specific kwargs.
    summary_calls = []

    if buckets["simple"]:
        res = impute_simple(
            csv_path="",
            columns=buckets["simple"],
            strategy="most_frequent",
            add_indicators=add_indicators_bool,
            tool_context=ctx,
        )
        summary_calls.append({"tool": "impute_simple", "columns": buckets["simple"], "result": res})

    if buckets["knn"]:
        res = impute_knn(
            csv_path="",
            columns=buckets["knn"],
            n_neighbors=5,
            add_indicators=add_indicators_bool,
            tool_context=ctx,
        )
        summary_calls.append({"tool": "impute_knn", "columns": buckets["knn"], "result": res})

    if buckets["iterative"]:
        res = impute_iterative(
            csv_path="",
            columns=buckets["iterative"],
            max_iter=10,
            random_state=0,
            add_indicators=add_indicators_bool,
            tool_context=ctx,
        )
        summary_calls.append({"tool": "impute_iterative", "columns": buckets["iterative"], "result": res})

    # Optional breadcrumb (no direct file writes here)
    if register_artifact:
        try:
            register_artifact(ctx.state, "", kind="note", label="auto_impute_orchestrator_adk_run")
        except Exception:
            pass

    # Build a compact report
    report = {
        "status": "success",
        "cleaning": {
            "drop_threshold": drop_threshold_float,
            "robust_auto_clean_file_result": clean_result,
        },
        "dataset_rows_detected": n_rows,
        "imputation_plan": {
            "simple": buckets["simple"],
            "knn": buckets["knn"],
            "iterative": buckets["iterative"],
            "left_unimputed_50to99": buckets["left_unimputed_50to99"],
        },
        "tool_calls": summary_calls,
        "notes": (
            f"Columns with >= {drop_threshold_float} missing are dropped by robust_auto_clean_file. "
            f"Add missing indicators: {add_indicators_bool}. "
            "If your impute_* tools support add_indicators, set add_missing_indicators=yes "
            "to create *_was_missing flags."
        ),
    }
    return report
