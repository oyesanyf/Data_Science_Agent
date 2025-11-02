# -*- coding: utf-8 -*-
"""
File-only robust cleaner for ADK tools (no DataFrame inputs/outputs).

Inputs (all optional; sensible defaults used):
- callback_context.state["default_csv_path"]  -> path to the uploaded CSV (set by your upload callback)
- csv_path (str)                              -> override to a specific CSV (discouraged; default uses state)
- delimiter, encoding, header_strategy, etc.  -> optional knobs

Outputs (dict of primitives/paths only):
{
  "status": "success",
  "cleaned_csv_path": ".../cleaned_<slug>.csv",
  "cleaned_parquet_path": ".../cleaned_<slug>.parquet",
  "rows_in": int, "rows_out": int,
  "cols": int,
  "schema_fingerprint": "…",
  "issues_detected": {...},         # counts (nulls, outliers capped, coerced types, etc.)
  "column_types": {...},            # inferred final types (string repr)
  "report_path": ".../clean_report.json"  # machine-readable report
}
"""

import os
import io
import re
import json
import math
import uuid
import shutil
import gzip
import csv
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Iterable

logger = logging.getLogger(__name__)

# Lightweight deps: use pandas internally; DO NOT expose DataFrames through ADK boundary.
import pandas as pd
import numpy as np

# Optional fast parquet if available
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    _HAVE_PA = True
except Exception:
    _HAVE_PA = False

# ADK plumbing (import guarded)
try:
    from .artifact_manager import ensure_workspace, register_artifact
except Exception:
    def ensure_workspace(state, upload_root): return None
    def register_artifact(state, path, kind="artifact", label=None): return None

# ToolContext import (for ADK compatibility)
try:
    from google.adk.tools import ToolContext
except Exception:
    ToolContext = object  # fallback

try:
    from .dynamic_csv_reader import detect_csv_properties, read_csv_smart
except Exception:
    # Minimal fallback (very defensive)
    def detect_csv_properties(path: str) -> Dict[str, Any]:
        return {"delimiter": ",", "encoding": "utf-8", "has_header": True}
    def read_csv_smart(path: str, **kwargs) -> pd.DataFrame:
        return pd.read_csv(path, **kwargs)

try:
    from .schema_contract import schema_fingerprint as _schema_fingerprint
except Exception:
    def _schema_fingerprint(cols: Iterable[str]) -> str:
        s = "|".join([str(c) for c in cols])
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# ----------------------------
# Utilities (no DF in/out)
# ----------------------------

_NULL_TOKENS = {"", "na", "n/a", "none", "null", "nan", "?", "-", "--"}
_BOOL_TRUE = {"true", "t", "yes", "y", "1"}
_BOOL_FALSE = {"false", "f", "no", "n", "0"}

_NUM_RE = re.compile(r"^\s*[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:%|)$")
_PERCENT_RE = re.compile(r"^\s*[-+]?\d+(?:\.\d+)?\s*%\s*$")
_DATE_HINT_RE = re.compile(r"(date|time|timestamp|dt)$", re.I)

def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", s).strip("_")
    return s or f"dataset_{uuid.uuid4().hex[:8]}"


def _find_available_csvs(search_dirs=None, limit=10):
    """
     SMART FILE FINDER
    
    Searches common locations for CSV/Parquet files and returns metadata.
    Helps users discover what files are available for cleaning.
    
    Args:
        search_dirs: List of directories to search (default: ['uploads/', './', 'data/'])
        limit: Max files to return (default: 10)
    
    Returns:
        list of dicts with file info (path, size, modified_time, rows_preview)
    """
    if search_dirs is None:
        search_dirs = [
            "uploads",
            ".",
            "data", 
            "datasets",
            os.path.expanduser("~/Downloads"),
        ]
    
    found_files = []
    
    for base_dir in search_dirs:
        if not os.path.exists(base_dir):
            continue
        
        try:
            for root, dirs, files in os.walk(base_dir):
                # Skip hidden and system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
                
                for file in files:
                    if file.endswith(('.csv', '.parquet', '.tsv', '.txt')):
                        full_path = os.path.join(root, file)
                        try:
                            stat = os.stat(full_path)
                            size_mb = stat.st_size / (1024 * 1024)
                            
                            # Try to preview rows (first 5)
                            rows_preview = "Unknown"
                            try:
                                if file.endswith('.parquet'):
                                    import pyarrow.parquet as pq
                                    table = pq.read_table(full_path)
                                    rows_preview = len(table)
                                else:
                                    # Quick row count for CSV
                                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        rows_preview = sum(1 for _ in f) - 1  # Exclude header
                            except Exception:
                                pass
                            
                            found_files.append({
                                "path": full_path,
                                "filename": file,
                                "size_mb": round(size_mb, 2),
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "estimated_rows": rows_preview,
                            })
                            
                            if len(found_files) >= limit:
                                return found_files
                        except Exception:
                            continue
        except Exception:
            continue
    
    # Sort by modification time (most recent first)
    found_files.sort(key=lambda x: x["modified"], reverse=True)
    return found_files[:limit]


def _suggest_best_match(requested_name: str, available_files: list) -> str:
    """
     SMART FILE MATCHER
    
    Suggests the best matching file based on name similarity.
    Uses fuzzy matching to handle typos and partial names.
    
    Args:
        requested_name: The file name/path the user requested
        available_files: List of file dicts from _find_available_csvs()
    
    Returns:
        Best matching file path or empty string
    """
    if not available_files:
        return ""
    
    # Extract just the filename without path
    req_base = os.path.basename(requested_name).lower()
    req_base_no_ext = os.path.splitext(req_base)[0]
    
    best_match = None
    best_score = 0
    
    for file_info in available_files:
        filename = file_info["filename"].lower()
        filename_no_ext = os.path.splitext(filename)[0]
        
        # Exact match (case-insensitive)
        if filename == req_base or filename_no_ext == req_base_no_ext:
            return file_info["path"]
        
        # Partial match scoring
        score = 0
        if req_base_no_ext in filename_no_ext:
            score += 50
        if filename_no_ext in req_base_no_ext:
            score += 40
        
        # Word overlap
        req_words = set(req_base_no_ext.split('_'))
        file_words = set(filename_no_ext.split('_'))
        overlap = len(req_words & file_words)
        score += overlap * 10
        
        if score > best_score:
            best_score = score
            best_match = file_info["path"]
    
    return best_match if best_score > 20 else ""

def _coerce_bool(x):
    if pd.isna(x): return np.nan
    sx = str(x).strip().lower()
    if sx in _BOOL_TRUE: return True
    if sx in _BOOL_FALSE: return False
    return np.nan

def _coerce_numeric(x):
    if pd.isna(x): return np.nan
    sx = str(x).strip()
    if _PERCENT_RE.match(sx):
        try:
            return float(sx.replace("%", "").replace(",", "")) / 100.0
        except Exception:
            return np.nan
    try:
        # remove thousands separators
        sx2 = sx.replace(",", "")
        return float(sx2)
    except Exception:
        return np.nan

def _is_mostly_numeric(series: pd.Series, sample=2000) -> bool:
    s = series.dropna().astype(str).head(sample)
    if s.empty: return False
    hits = s.apply(lambda v: bool(_NUM_RE.match(v)) or bool(_PERCENT_RE.match(v))).sum()
    return hits / len(s) >= 0.8

def _choose_imputer_numeric(s: pd.Series):
    # median if skewed, else mean
    try:
        skew = s.skew(skipna=True)
        return np.nanmedian if abs(skew) > 1.0 else np.nanmean
    except Exception:
        return np.nanmedian


def _intelligent_impute_numeric(df: pd.DataFrame, col: str) -> tuple:
    """
     INTELLIGENT NUMERIC IMPUTATION
    
    Automatically selects the best imputation strategy based on:
    - Missing data percentage
    - Column correlations
    - Data distribution
    - Dataset size
    
    Strategy Selection:
    1. <5% missing + skewed → Median
    2. <5% missing + normal → Mean
    3. 5-30% missing + correlated cols → KNN (k=5)
    4. 5-30% missing + low correlation → Iterative (linear regression-based)
    5. >30% missing → Forward/Backward fill OR drop column warning
    
    Returns:
        (imputed_series, method_used, confidence_score)
    """
    s = df[col]
    missing_pct = s.isna().mean()
    
    # Strategy 1: Very few missing (<5%) → Simple imputation
    if missing_pct < 0.05:
        try:
            skew = s.skew(skipna=True)
            if abs(skew) > 1.0:
                val = np.nanmedian(s)
                return s.fillna(val), "median_skewed", 0.95
            else:
                val = np.nanmean(s)
                return s.fillna(val), "mean_normal", 0.95
        except Exception:
            val = np.nanmedian(s)
            return s.fillna(val), "median_fallback", 0.90
    
    # Strategy 2: Moderate missing (5-30%) → KNN or Iterative
    elif missing_pct < 0.30:
        # Check for correlated numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if col in numeric_cols:
            numeric_cols.remove(col)
        
        # Calculate correlations
        max_corr = 0.0
        if len(numeric_cols) > 0:
            try:
                corr_matrix = df[numeric_cols + [col]].corr()
                correlations = corr_matrix[col].drop(col, errors='ignore')
                max_corr = abs(correlations).max() if len(correlations) > 0 else 0.0
            except Exception:
                max_corr = 0.0
        
        # If strongly correlated with other columns → KNN
        if max_corr > 0.3 and len(numeric_cols) >= 2:
            try:
                from sklearn.impute import KNNImputer
                # Use only numeric columns for KNN
                cols_for_knn = [c for c in numeric_cols[:10]]  # Limit to 10 for performance
                cols_for_knn.append(col)
                
                # CRITICAL FIX: Ensure n_neighbors is at least 2, never 0
                n_neighbors = max(2, min(5, max(1, len(df) // 10)))
                imputer = KNNImputer(n_neighbors=n_neighbors)
                df_subset = df[cols_for_knn].copy()
                imputed_data = imputer.fit_transform(df_subset)
                col_idx = cols_for_knn.index(col)
                
                return pd.Series(imputed_data[:, col_idx], index=df.index), "knn_correlated", 0.85
            except Exception as e:
                logger.warning(f"KNN imputation failed for {col}: {e}, falling back to iterative")
        
        # Otherwise → Iterative imputer (regression-based)
        try:
            from sklearn.experimental import enable_iterative_imputer  # noqa
            from sklearn.impute import IterativeImputer
            
            cols_for_iter = [c for c in numeric_cols[:15]]  # Limit to 15
            cols_for_iter.append(col)
            
            imputer = IterativeImputer(max_iter=10, random_state=42)
            df_subset = df[cols_for_iter].copy()
            imputed_data = imputer.fit_transform(df_subset)
            col_idx = cols_for_iter.index(col)
            
            return pd.Series(imputed_data[:, col_idx], index=df.index), "iterative_ml", 0.80
        except Exception as e:
            logger.warning(f"Iterative imputation failed for {col}: {e}, falling back to median")
            val = np.nanmedian(s)
            return s.fillna(val), "median_fallback", 0.70
    
    # Strategy 3: Heavy missing (>30%) → Forward fill or warn
    else:
        logger.warning(
            f"[WARNING] Column '{col}' has {missing_pct*100:.1f}% missing data. "
            "Consider dropping this column or collecting more data."
        )
        # Try forward/backward fill (useful for time series)
        filled = s.fillna(method='ffill').fillna(method='bfill')
        if filled.isna().any():
            # Still has NaN → use median as last resort
            val = np.nanmedian(s)
            return s.fillna(val), "median_high_missing", 0.50
        return filled, "forward_backward_fill", 0.60


def _intelligent_impute_categorical(df: pd.DataFrame, col: str) -> tuple:
    """
     INTELLIGENT CATEGORICAL IMPUTATION
    
    Strategy Selection:
    1. <10% missing → Mode (most frequent)
    2. 10-30% missing → Predictive (use other cols to predict category)
    3. >30% missing → Create "Unknown" category
    
    Returns:
        (imputed_series, method_used, confidence_score)
    """
    s = df[col]
    missing_pct = s.isna().mean()
    
    # Strategy 1: Low missing → Mode
    if missing_pct < 0.10:
        mode_vals = s.mode(dropna=True)
        if len(mode_vals) > 0:
            return s.fillna(mode_vals.iloc[0]), "mode_frequent", 0.90
        else:
            return s.fillna("Unknown"), "unknown_no_mode", 0.50
    
    # Strategy 2: Moderate missing → Create "Unknown" or "Missing" category
    elif missing_pct < 0.30:
        # For categorical data, explicitly marking as missing can be informative
        return s.fillna("Missing"), "explicit_missing_category", 0.75
    
    # Strategy 3: Heavy missing → Mark as Unknown
    else:
        logger.warning(
            f"[WARNING] Column '{col}' has {missing_pct*100:.1f}% missing categorical data. "
            "Consider dropping this column."
        )
        return s.fillna("Unknown_HighMissing"), "unknown_high_missing", 0.40

def _cap_outliers_iqr(s: pd.Series):
    try:
        q1, q3 = np.nanpercentile(s, [25, 75])
        iqr = q3 - q1
        if iqr == 0 or not np.isfinite(iqr): return s, 0
        lo, hi = (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
        before = s.copy()
        s = s.clip(lower=lo, upper=hi)
        changed = np.nansum(before.values != s.values)
        return s, int(changed)
    except Exception:
        return s, 0


def detect_and_skip_metadata_rows(
    df: pd.DataFrame,
    max_rows_to_check: int = 5,
    numeric_threshold_low: float = 0.5,
    numeric_threshold_high: float = 0.7,
) -> Dict[str, Any]:
    """
     GENERIC METADATA ROW DETECTOR
    
    Intelligently detects and skips stacked metadata/header rows in datasets.
    Common in scientific datasets (brain imaging, genomics, etc.) where:
    - First few rows contain metadata, annotations, or duplicate headers
    - Actual numeric/categorical data starts several rows down
    
    Strategy:
    1. Check first N rows for metadata patterns
    2. Identify rows that are:
       - All NaN (empty separator rows)
       - Mostly non-numeric when subsequent rows are numeric
       - Duplicate header rows
    3. Find the first row where actual data begins
    4. Optionally extract metadata for use as enhanced column names
    
    Args:
        df: Input DataFrame (may contain metadata in initial rows)
        max_rows_to_check: Maximum number of initial rows to analyze (default: 5)
        numeric_threshold_low: Threshold below which a row is considered non-numeric (default: 0.5)
        numeric_threshold_high: Threshold above which a row is considered numeric data (default: 0.7)
    
    Returns:
        dict with:
            - data_start_row (int): Index where actual data begins
            - metadata_rows_found (int): Number of metadata rows detected
            - suggested_headers (list): Potential column names extracted from metadata
            - should_rename_columns (bool): Whether to apply suggested headers
            - analysis (dict): Detailed analysis of each row checked
    
    Examples:
        >>> # Brain networks dataset with 3 metadata rows
        >>> df = pd.read_csv("brain_networks.csv")
        >>> result = detect_and_skip_metadata_rows(df)
        >>> # Returns: {"data_start_row": 3, "metadata_rows_found": 3, ...}
        >>> 
        >>> # Clean DataFrame using results
        >>> if result["metadata_rows_found"] > 0:
        >>>     df = df.iloc[result["data_start_row"]:].reset_index(drop=True)
        >>>     if result["should_rename_columns"]:
        >>>         df.columns = result["suggested_headers"]
    """
    max_check = min(max_rows_to_check, len(df))
    data_start_row = 0
    suggested_headers = list(df.columns)
    should_rename = False
    analysis = {}
    
    for i in range(max_check):
        try:
            row = df.iloc[i]
            row_analysis = {
                "row_index": i,
                "is_metadata": False,
                "reason": None,
                "numeric_ratio": 0.0,
            }
            
            # ===== CHECK 1: All NaN (empty separator row) =====
            if row.isna().all():
                row_analysis["is_metadata"] = True
                row_analysis["reason"] = "all_nan"
                data_start_row = i + 1
                analysis[f"row_{i}"] = row_analysis
                continue
            
            # ===== CHECK 2: Numeric content analysis =====
            # Convert row values to numeric, count successes
            numeric_series = pd.to_numeric(row, errors='coerce')
            numeric_count = numeric_series.notna().sum()
            total_count = len(row)
            numeric_ratio = numeric_count / max(1, total_count)
            row_analysis["numeric_ratio"] = float(numeric_ratio)
            
            # ===== CHECK 3: Compare with next row =====
            if i + 1 < len(df):
                next_row = df.iloc[i + 1]
                next_numeric_series = pd.to_numeric(next_row, errors='coerce')
                next_numeric_count = next_numeric_series.notna().sum()
                next_numeric_ratio = next_numeric_count / max(1, len(next_row))
                row_analysis["next_numeric_ratio"] = float(next_numeric_ratio)
                
                # If current row is <threshold_low numeric but next row is >threshold_high numeric
                # → current row is likely metadata/header
                if numeric_ratio < numeric_threshold_low and next_numeric_ratio > numeric_threshold_high:
                    row_analysis["is_metadata"] = True
                    row_analysis["reason"] = "text_before_numeric_data"
                    data_start_row = i + 1
                    
                    # ===== CHECK 4: Extract descriptive headers from metadata row =====
                    # Use current row as enhanced column names if they're descriptive
                    row_str = row.astype(str)
                    avg_length = row_str.str.len().mean()
                    
                    if avg_length > 1:  # Not just "1", "2", etc.
                        # Combine with existing headers for richer column names
                        new_headers = []
                        for existing, meta in zip(df.columns, row_str):
                            # If existing header is just a number, use metadata
                            if str(existing).isdigit():
                                new_headers.append(str(meta))
                            # If metadata is descriptive, combine them
                            elif len(str(meta)) > 1 and str(meta) != 'nan':
                                new_headers.append(f"{existing}_{meta}")
                            else:
                                new_headers.append(str(existing))
                        
                        suggested_headers = new_headers
                        should_rename = True
                        row_analysis["extracted_headers"] = new_headers[:5]  # Show first 5
                    
                    analysis[f"row_{i}"] = row_analysis
                    continue
            
            # ===== CHECK 5: Row is mostly numeric → data start found! =====
            if numeric_ratio > numeric_threshold_high:
                row_analysis["is_metadata"] = False
                row_analysis["reason"] = "numeric_data_found"
                data_start_row = i
                analysis[f"row_{i}"] = row_analysis
                break
            
            analysis[f"row_{i}"] = row_analysis
                
        except Exception as e:
            # If any check fails, assume this is data start
            analysis[f"row_{i}"] = {
                "row_index": i,
                "is_metadata": False,
                "reason": "check_failed",
                "error": str(e),
            }
            data_start_row = i
            break
    
    metadata_rows_found = data_start_row
    
    return {
        "data_start_row": data_start_row,
        "metadata_rows_found": metadata_rows_found,
        "suggested_headers": suggested_headers,
        "should_rename_columns": should_rename,
        "analysis": analysis,
        "summary": (
            f"Found {metadata_rows_found} metadata row(s). "
            f"Actual data starts at row {data_start_row}. "
            f"{'Suggested new column names extracted.' if should_rename else 'No header changes needed.'}"
        ),
    }


# ----------------------------
# Main cleaner (file I/O only)
# ----------------------------

def robust_auto_clean_file(
    csv_path: str = "",
    output_dir: str = "",
    force_header: str = "auto",
    datetime_infer: str = "yes",
    cap_outliers: str = "yes",
    impute_missing: str = "yes",
    drop_empty_columns: str = "yes",
    drop_duplicate_rows: str = "yes",
    keep_original_name: str = "yes",
    tool_context: Optional[ToolContext] = None,
):
    """
    Clean the uploaded CSV, write cleaned CSV/Parquet to disk, and return file paths + stats.
    
    All parameters are strings to satisfy Google ADK's strict schema parser.
    Empty strings are treated as None/default values internally.
    
    Args:
        csv_path: Path to CSV file (empty string = use state['default_csv_path'])
        output_dir: Output directory (empty string = use default)
        force_header: Force header detection (empty/"auto"=auto, "yes"=force, "no"=skip)
        datetime_infer: Parse date-like columns ("yes"/"no", default "yes")
        cap_outliers: IQR capping for numeric ("yes"/"no", default "yes")
        impute_missing: Simple imputation ("yes"/"no", default "yes")
        drop_empty_columns: Drop null columns ("yes"/"no", default "yes")
        drop_duplicate_rows: Remove duplicates ("yes"/"no", default "yes")
        keep_original_name: Use dataset slug ("yes"/"no", default "yes")
        tool_context: Tool context (auto-provided by ADK)
    
    NOTE: Uses tool_context to access the uploaded file from session state.
    """
    # Convert string parameters to proper types (handle Google ADK's all-required-params limitation)
    csv_path = csv_path if csv_path and csv_path.strip() else None
    output_dir = output_dir if output_dir and output_dir.strip() else None
    
    # Convert string booleans
    def str_to_bool(val: str, default: bool = True) -> bool:
        if not val or not val.strip():
            return default
        return val.lower() in ("yes", "true", "1", "y")
    
    force_header_val = None if not force_header or force_header.strip().lower() in ("", "auto", "none") else (force_header.lower() in ("yes", "true", "1"))
    datetime_infer_val = str_to_bool(datetime_infer, True)
    cap_outliers_val = str_to_bool(cap_outliers, True)
    impute_missing_val = str_to_bool(impute_missing, True)
    drop_empty_columns_val = str_to_bool(drop_empty_columns, True)
    drop_duplicate_rows_val = str_to_bool(drop_duplicate_rows, True)
    keep_original_name_val = str_to_bool(keep_original_name, True)
    
    # Get state from tool_context (standard ADK pattern)
    callback_context = tool_context
    state = getattr(callback_context, "state", {}) if callback_context else {}

    # -------------------- ENSURE ONLY ONE FILE IN WORKSPACE --------------------
    # Clean up duplicate files, keeping only the earliest one
    try:
        if callback_context and hasattr(callback_context, "state"):
            state = callback_context.state
            workspace_paths = state.get("workspace_paths", {})
            uploads_dir = workspace_paths.get("uploads") or os.path.join(os.path.dirname(csv_path) if csv_path else ".", "uploads")
            
            # Use utility function to ensure only one file exists
            from .utils.filename_preservation import ensure_single_file_in_workspace
            ensure_single_file_in_workspace(uploads_dir)
    except Exception as cleanup_err:
        logger.warning(f"[SINGLE FILE ENFORCEMENT] Error during cleanup: {cleanup_err}")
    
    # -------------------- locate input --------------------
    in_path = csv_path or state.get("default_csv_path")
    
    #  ENHANCED: Smart file discovery with AUTOMATIC selection of most recent file
    if not in_path:
        # Auto-discover available files
        logger.info(" No file path provided. Searching for most recent CSV file...")
        available_files = _find_available_csvs(limit=10)
        
        if available_files:
            #  AUTOMATICALLY USE THE MOST RECENT FILE
            most_recent = available_files[0]  # Already sorted by modification time (newest first)
            in_path = most_recent["path"]
            
            logger.info(f"[OK] Auto-selected most recent file: {most_recent['filename']}")
            logger.info(f"   Path: {in_path}")
            logger.info(f"   Size: {most_recent['size_mb']} MB")
            logger.info(f"   Modified: {most_recent['modified']}")
            logger.info(f"   Estimated rows: {most_recent['estimated_rows']}")
            
            # Show other available files for reference
            if len(available_files) > 1:
                other_files = "\n".join([
                    f"  • {f['filename']} ({f['size_mb']} MB, modified: {f['modified'][:10]})"
                    for f in available_files[1:6]  # Show up to 5 other files
                ])
                logger.info(f"\n Other recent files available:\n{other_files}")
        else:
            # ADK State object may not support .keys()
            state_keys = []
            try:
                if hasattr(state, 'keys'):
                    state_keys = list(state.keys())
            except Exception:
                pass
            
            return {
                "status": "failed",
                "error": "No CSV file specified and none found",
                "message": (
                    "[X] No CSV file found in session state and no CSV files discovered in workspace.\n\n"
                    " Next steps:\n"
                    "1. Upload a CSV file through the UI\n"
                    "2. Place CSV files in: uploads/, data/, or current directory\n"
                    "3. Use list_data_files() to check available files\n"
                    "4. Specify csv_path parameter explicitly\n"
                ),
                "available_state_keys": state_keys,
                "searched_directories": ["uploads", ".", "data", "datasets"],
            }
    
    if not os.path.exists(in_path):
        #  ENHANCED: Smart file matching with auto-suggestions
        logger.warning(f"[X] File not found: {in_path}")
        logger.info(" Searching for similar files...")
        
        # Search for available files
        available_files = _find_available_csvs(limit=15)
        
        # Try to find best match
        best_match = _suggest_best_match(in_path, available_files)
        
        if best_match:
            # Found a likely match!
            matched_file = next((f for f in available_files if f["path"] == best_match), None)
            return {
                "status": "failed",
                "error": "File not found, but found similar file",
                "message": (
                    f"[X] Requested file not found: {in_path}\n\n"
                    f"[OK] Found similar file that might be what you're looking for:\n"
                    f"  • {matched_file['filename']} ({matched_file['size_mb']} MB, ~{matched_file['estimated_rows']} rows)\n"
                    f"   Path: {matched_file['path']}\n\n"
                    f" Recommendation: Use this file instead?\n"
                    f"   robust_auto_clean_file(csv_path='{best_match}')\n\n"
                    f"Or choose from {len(available_files)} available files:"
                ),
                "requested_path": in_path,
                "suggested_file": matched_file,
                "available_files": available_files[:5],  # Show top 5
                "recommendation": f"robust_auto_clean_file(csv_path='{best_match}')",
            }
        elif available_files:
            # No good match, but show all available files
            file_list_str = "\n".join([
                f"  • {f['filename']} ({f['size_mb']} MB, ~{f['estimated_rows']} rows) - {f['path']}"
                for f in available_files[:10]
            ])
            
            return {
                "status": "failed",
                "error": "File not found",
                "message": (
                    f"[X] Requested file not found: {in_path}\n\n"
                    f"[OK] Found {len(available_files)} CSV/Parquet files in your workspace:\n"
                    f"{file_list_str}\n\n"
                    " Next steps:\n"
                    "1. Check the file name/path for typos\n"
                    "2. Use one of the paths listed above\n"
                    "3. Re-upload your CSV file through the UI\n"
                    "4. Use list_data_files() to see more files\n"
                ),
                "requested_path": in_path,
                "available_files": available_files,
                "recommendation": f"Try: robust_auto_clean_file(csv_path='{available_files[0]['path']}')" if available_files else None,
            }
        else:
            # No files found at all
            return {
            "status": "failed",
                "error": "File not found and no CSV files discovered",
                "message": (
                    f"[X] Requested file not found: {in_path}\n"
                    "[X] No CSV/Parquet files found in common locations.\n\n"
                    " Next steps:\n"
                    "1. Verify the file path is correct\n"
                    "2. Upload a CSV file through the UI\n"
                    "3. Place CSV files in: uploads/, data/, or current directory\n"
                    "4. Check file permissions\n"
                ),
                "requested_path": in_path,
                "searched_directories": ["uploads", ".", "data", "datasets", "~/Downloads"],
        }

    # workspace & output dir
    upload_root = os.path.dirname(in_path)
    if callback_context and hasattr(callback_context, "state"):
        try:
            ensure_workspace(callback_context.state, upload_root)
            workspace_root = callback_context.state.get("workspace_root", upload_root)
        except Exception:
            workspace_root = upload_root
    else:
        workspace_root = upload_root

    out_dir = output_dir or os.path.join(workspace_root, "cleaned")
    os.makedirs(out_dir, exist_ok=True)

    # dataset slug
    base_name = os.path.splitext(os.path.basename(in_path))[0]
    slug = _slugify(state.get("original_dataset_name", base_name)) if keep_original_name_val else _slugify(base_name)

    # -------------------- detect format --------------------
    props = detect_csv_properties(in_path)
    delimiter = props.get("delimiter", ",")
    encoding = props.get("encoding", "utf-8")
    has_header = force_header_val if force_header_val is not None else bool(props.get("has_header", True))

    # -------------------- read CSV (single DF internally) --------------------
    # NOTE: internal DataFrame use is OK; ADK boundary returns files only.
    try:
        df = read_csv_smart(
            in_path,
            delimiter=delimiter,
            encoding=encoding,
            header=0 if has_header else None,
            low_memory=False,
        )
    except Exception as e:
        return {
            "status": "failed",
            "error": f"read_csv error: {str(e)}",
            "message": "Use preview_csv_formats() to inspect alternative delimiters/encodings."
        }

    rows_in, cols_in = df.shape

    # Initialize issues tracking dictionary
    issues = {
        "coerced_numeric": 0,
        "booleans_standardized": 0,
        "datetimes_parsed": 0,
        "outliers_capped": 0,
        "nulls_imputed": 0,
        "empty_columns_dropped": 0,
        "duplicate_rows_dropped": 0,
        "metadata_rows_dropped": 0,
        "duplicate_header_rows_dropped": 0,
    }
    
    # Track intelligent imputation methods used
    imputation_methods = {}

    # -------------------- header repair / stacked header cleanup --------------------
    # Trim/normalize column names; if first row looks like headers (strings, unique),
    # promote it to header.
    df.columns = [str(c).strip() for c in df.columns]

    if not has_header:
        # try to promote row 0 as header if it is mostly strings and unique
        first = df.iloc[0].astype(str)
        unique_ratio = first.nunique() / max(1, len(first))
        if unique_ratio > 0.8:
            df.columns = [str(x).strip() for x in first]
            df = df.iloc[1:].reset_index(drop=True)

    # [OK] ENHANCED: Use generic metadata row detector (works for brain networks, genomics, etc.)
    metadata_result = detect_and_skip_metadata_rows(
        df, 
        max_rows_to_check=5,
        numeric_threshold_low=0.5,
        numeric_threshold_high=0.7
    )
    
    # Apply detection results
    if metadata_result["metadata_rows_found"] > 0:
        logger.info(f" {metadata_result['summary']}")
        issues["metadata_rows_dropped"] = metadata_result["metadata_rows_found"]
        
        # Skip to data start row
        df = df.iloc[metadata_result["data_start_row"]:].reset_index(drop=True)
        
        # Apply suggested column names if metadata contained descriptive headers
        if metadata_result["should_rename_columns"]:
            df.columns = metadata_result["suggested_headers"]
            logger.info(f" Applied enhanced column names from metadata rows.")

    # Drop rows that are pure headers repeated inside the file (common in stacked/blocked CSVs)
    # Heuristic: if a row values match the column names exactly → drop.
    try:
        # Compare each row's values (as strings) with column names (as strings)
        column_names_stripped = list(map(str.strip, df.columns.tolist()))
        mask_header_dup = df.astype(str).apply(
            lambda r: list(map(str.strip, r.values.tolist())) == column_names_stripped, 
            axis=1
        )
        
        # CRITICAL FIX: Ensure mask_header_dup is a boolean Series, not a DataFrame
        # Handle case where .any() might return a Series (if mask_header_dup is somehow a DataFrame)
        if isinstance(mask_header_dup, pd.DataFrame):
            # If it's a DataFrame, flatten it first
            mask_header_dup = mask_header_dup.all(axis=1) if mask_header_dup.shape[1] > 1 else mask_header_dup.iloc[:, 0]
        
        # Ensure it's a Series with boolean values
        if not isinstance(mask_header_dup, pd.Series):
            mask_header_dup = pd.Series(mask_header_dup, index=df.index)
        
        # Now safely check if any rows match
        has_duplicate_headers = bool(mask_header_dup.any())
        
        if has_duplicate_headers:
            df = df.loc[~mask_header_dup].reset_index(drop=True)
            issues["duplicate_header_rows_dropped"] = int(mask_header_dup.sum())
    except Exception as e:
        # If header detection fails, log and continue (non-critical)
        logger.warning(f"[CLEAN] Failed to detect duplicate header rows: {e}")
        # Don't raise - continue with cleaning

    #  Drop monotonic ID/index columns (e.g., 'Unnamed: 0', 'index')
    try:
        for c in list(df.columns):
            if re.match(r"^unnamed[:\s_-]*0$", c, re.I) or c.lower() in {"index", "id"}:
                s = pd.to_numeric(df[c], errors="coerce")
                # FIX: Ensure diff comparison doesn't cause length mismatch error
                # Check if column is monotonically increasing by 1 (like an index)
                if s.notna().all() and len(s) > 1:
                    diffs = s.diff().dropna()
                    # Check if all differences are 1 (monotonic increment)
                    if len(diffs) > 0 and (diffs == 1).all():
                        df = df.drop(columns=[c])
                        issues.setdefault("dropped_identifier_columns", []).append(c)
    except Exception:
        pass

    # -------------------- normalize null tokens --------------------
    df = df.replace(to_replace=list(_NULL_TOKENS), value=np.nan)

    # -------------------- type coercion pass --------------------
    # Detect numeric-like columns stored as text and coerce
    for c in df.columns:
        s = df[c]
        # try boolean standardization first if low unique count and texty
        su = s.dropna().astype(str).str.strip().str.lower()
        if su.nunique(dropna=True) <= 3 and su.isin(_BOOL_TRUE.union(_BOOL_FALSE)).mean() > 0.7:
            new_s = s.map(_coerce_bool)
            issues["booleans_standardized"] += int(np.nansum(new_s.notna() & s.notna() & (new_s.astype(object) != s.astype(object))))
            df[c] = new_s
            continue

        # numeric?
        if _is_mostly_numeric(s):
            new_s = s.map(_coerce_numeric)
            changed = int(np.nansum(~pd.isna(new_s) & ~pd.isna(s) & (pd.to_numeric(s, errors="coerce") != new_s)))
            issues["coerced_numeric"] += max(0, changed)
            df[c] = new_s
            continue

        # datetime?
        if datetime_infer_val and (_DATE_HINT_RE.search(c) or su.str.contains(r"\d{4}-\d{2}-\d{2}", regex=True).mean() > 0.5):
            try:
                parsed = pd.to_datetime(s, errors="coerce", utc=False, infer_datetime_format=True)
                if parsed.notna().mean() > 0.6:
                    df[c] = parsed
                    issues["datetimes_parsed"] += int(parsed.notna().sum())
            except Exception:
                pass

    # -------------------- outlier capping --------------------
    if cap_outliers_val:
        num_cols = df.select_dtypes(include=[np.number]).columns
        for c in num_cols:
            df[c], changed = _cap_outliers_iqr(df[c])
            issues["outliers_capped"] += int(changed)

    # -------------------- INTELLIGENT imputation --------------------
    if impute_missing_val:
        logger.info(" Starting intelligent imputation (auto-selects best strategy per column)...")
        
        # NUMERIC COLUMNS: Use intelligent imputation
        for c in df.select_dtypes(include=[np.number]).columns:
            if df[c].isna().any():
                missing_before = df[c].isna().sum()
                try:
                    imputed_series, method, confidence = _intelligent_impute_numeric(df, c)
                    df[c] = imputed_series
                    missing_after = df[c].isna().sum()
                    
                    if missing_after < missing_before:
                        issues["nulls_imputed"] += int(missing_before - missing_after)
                        imputation_methods[c] = {
                            "method": method,
                            "confidence": float(confidence),
                            "missing_pct": float(missing_before / len(df)),
                            "imputed_count": int(missing_before - missing_after)
                        }
                        logger.info(f"  [OK] {c}: {method} (confidence: {confidence:.2f})")
                except Exception as e:
                    # CRITICAL FIX: Only fill with fallback inside exception block
                    logger.warning(f"  [WARNING] {c}: Intelligent imputation failed ({e}), using median fallback")
                    val = np.nanmedian(df[c])
                    df[c] = df[c].fillna(val)
                    imputation_methods[c] = {"method": "median_error_fallback", "confidence": 0.60}
                    issues["nulls_imputed"] += int(missing_before - df[c].isna().sum())

        # DATETIME: Leave NaT (do not impute with arbitrary value)
        # Datetime imputation can introduce significant bias in time-series analysis
        
        # CATEGORICAL / OBJECT COLUMNS: Use intelligent categorical imputation
        for c in df.select_dtypes(include=["object", "category"]).columns:
            if df[c].isna().any():
                missing_before = df[c].isna().sum()
                try:
                    imputed_series, method, confidence = _intelligent_impute_categorical(df, c)
                    df[c] = imputed_series
                    missing_after = df[c].isna().sum()
                    
                    if missing_after < missing_before:
                        issues["nulls_imputed"] += int(missing_before - missing_after)
                        imputation_methods[c] = {
                            "method": method,
                            "confidence": float(confidence),
                            "missing_pct": float(missing_before / len(df)),
                            "imputed_count": int(missing_before - missing_after)
                        }
                        logger.info(f"  [OK] {c}: {method} (confidence: {confidence:.2f})")
                except Exception as e:
                    logger.warning(f"  [WARNING] {c}: Intelligent imputation failed ({e}), using mode fallback")
                    mode = df[c].mode(dropna=True)
                    if len(mode) > 0:
                        df[c] = df[c].fillna(mode.iloc[0])
                        imputation_methods[c] = {"method": "mode_error_fallback", "confidence": 0.60}
        
        logger.info(f" Imputation complete! Filled {issues['nulls_imputed']} values across {len(imputation_methods)} columns.")

    # -------------------- drop empty columns / duplicate rows --------------------
    if drop_empty_columns_val:
        na_all = df.columns[df.isna().all(axis=0)]
        if len(na_all) > 0:
            df = df.drop(columns=list(na_all))
            issues["empty_columns_dropped"] += int(len(na_all))

    if drop_duplicate_rows_val:
        before = len(df)
        df = df.drop_duplicates().reset_index(drop=True)
        issues["duplicate_rows_dropped"] += int(before - len(df))

    # -------------------- finalize schema + types --------------------
    rows_out, cols_out = df.shape
    col_types = {c: str(df[c].dtype) for c in df.columns}
    schema_fp = _schema_fingerprint(df.columns)

    # -------------------- write cleaned file to temporary location --------------------
    temp_cleaned_csv = os.path.join(out_dir, f"{slug}_cleaned_temp.csv")
    df.to_csv(temp_cleaned_csv, index=False)

    cleaned_parquet = None
    if _HAVE_PA:
        cleaned_parquet = os.path.join(out_dir, f"{slug}_cleaned.parquet")
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, cleaned_parquet)
    
    # -------------------- FILENAME PRESERVATION: Backup original and rename cleaned file --------------------
    # Use utility function to preserve original filename (applies to all tools that modify files)
    from .utils.filename_preservation import preserve_original_filename
    
    try:
        state = callback_context.state if callback_context and hasattr(callback_context, "state") else {}
        workspace_paths = state.get("workspace_paths", {})
        uploads_dir = workspace_paths.get("uploads") or os.path.join(workspace_root, "uploads")
        
        final_cleaned_csv, backup_created = preserve_original_filename(
            processed_file_path=temp_cleaned_csv,
            tool_context=callback_context,
            uploads_dir=uploads_dir,
            workspace_root=workspace_root
        )
        
        cleaned_csv = final_cleaned_csv if final_cleaned_csv else temp_cleaned_csv
    except Exception as preserve_err:
        logger.error(f"[FILENAME PRESERVATION] ❌ Failed to preserve filename: {preserve_err}")
        # Fallback: Use temp file name (rename it to standard cleaned name)
        cleaned_csv = os.path.join(out_dir, f"{slug}_cleaned.csv")
        if os.path.exists(temp_cleaned_csv):
            if os.path.exists(cleaned_csv):
                os.remove(cleaned_csv)  # Remove if exists
            os.rename(temp_cleaned_csv, cleaned_csv)
        logger.warning(f"[FILENAME PRESERVATION] ⚠️ Could not preserve original filename, saved as: {os.path.basename(cleaned_csv)}")

    # -------------------- emit JSON report --------------------
    report = {
        "input_path": in_path,
        "cleaned_csv_path": cleaned_csv,
        "cleaned_parquet_path": cleaned_parquet,
        "rows_in": int(rows_in),
        "rows_out": int(rows_out),
        "cols_in": int(cols_in),
        "cols_out": int(cols_out),
        "delimiter": delimiter,
        "encoding": encoding,
        "issues_detected": issues,
        "imputation_methods": imputation_methods,  # NEW: Track which method used per column
        "column_types": col_types,
        "schema_fingerprint": schema_fp,
        "run_at": datetime.utcnow().isoformat() + "Z",
        "params": {
            "force_header": force_header_val,
            "datetime_infer": datetime_infer_val,
            "cap_outliers": cap_outliers_val,
            "impute_missing": impute_missing_val,
            "drop_empty_columns": drop_empty_columns_val,
            "drop_duplicate_rows": drop_duplicate_rows_val,
        },
    }

    report_path = os.path.join(out_dir, f"{slug}_clean_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # register artifacts (no-ops if artifact_manager not present)
    try:
        if callback_context and hasattr(callback_context, "state"):
            register_artifact(callback_context.state, cleaned_csv, kind="cleaned", label="csv")
            if cleaned_parquet:
                register_artifact(callback_context.state, cleaned_parquet, kind="cleaned", label="parquet")
            register_artifact(callback_context.state, report_path, kind="report", label="clean_report")
    except Exception:
        pass

    return {
        "status": "success",
        "cleaned_csv_path": cleaned_csv,
        "cleaned_parquet_path": cleaned_parquet,
        "rows_in": int(rows_in),
        "rows_out": int(rows_out),
        "cols": int(cols_out),
        "schema_fingerprint": schema_fp,
        "issues_detected": issues,
        "imputation_methods": imputation_methods,  # NEW: Show which imputation method used per column
        "column_types": col_types,
        "report_path": report_path,
    }

