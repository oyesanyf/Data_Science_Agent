"""
Robust Streaming CSV Reader with Incremental Numeric Profiling

Features:
- Engine fallback: pyarrow → c engine automatically
- Encoding fallback: utf-8 → utf-8-sig → latin-1
- Bad lines safe: on_bad_lines="skip" with optional na_values
- Per-column, correct stats: Welford/Chan merge for numerical stability
- Null & coercion aware: safely handles mixed types
- Min/Max/Sum tracked: streaming, no full materialization
- Automatic inference: detects numeric columns from first chunk
- Progress hooks: progress_cb(rows_processed) for live status
- Remote paths: supports s3://, gs://, http(s):// when fsspec is available
- CSV only: Parquet support is disabled per project requirements

Usage Examples:
    # Stream chunks without loading entire file
    for chunk in read_csv_chunks("large_file.csv", chunksize=250_000):
        process_chunk(chunk)
    
    # Get numeric statistics without loading full dataset
    stats = incremental_numeric_profile(
        "large_file.csv",
        numeric_cols=None,  # Auto-infer from first chunk
        chunksize=250_000,
        progress_cb=lambda rows: print(f"Processed {rows} rows")
    )
    # Returns: {column: {"count": n, "mean": m, "std": s, "min": x, "max": y, "sum": z, "nulls": k}}
    
    # Estimate file info without full read
    info = estimate_file_info("large_file.csv")
    # Returns: {"file_size_bytes": ..., "file_size_mb": ..., "estimated_rows": ..., ...}

Integration Notes:
    This module is designed for use with large CSV files (>1M rows) where loading
    the entire dataset into memory is impractical. For smaller files, use the
    standard pandas read_csv() or utils.io.read_dataset() functions.

    Recommended integration points:
    - analyze_dataset_tool: Use incremental_numeric_profile() for large files
    - describe_tool: Use streaming stats for numeric columns when file is large
    - Any tool that needs to process GB+ datasets without memory spikes
"""

from __future__ import annotations

import os
import math
import warnings
from typing import Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union
from pathlib import Path

import numpy as np
import pandas as pd


# ----------------------------
# Robust CSV Chunk Reader
# ----------------------------

def _choose_engine(preferred: Optional[str] = "pyarrow") -> str:
    """
    Choose a stable pandas CSV engine with graceful fallback.
    
    Note: Parquet/pyarrow is NOT used for reading - this is just for CSV engine selection.
    """
    if preferred == "pyarrow":
        try:
            # Check if pyarrow CSV engine is available (not parquet)
            import pyarrow.csv as pv  # noqa: F401
            return "pyarrow"
        except Exception:
            pass
    # pandas >= 2.0 uses 'c' or 'python'; 'c' is fastest
    return "c"


def _try_read_csv(
    path: str,
    *,
    chunksize: int,
    usecols: Optional[Sequence[str]] = None,
    dtypes: Optional[Dict[str, str]] = None,
    delimiter: Optional[str] = None,
    compression: Union[str, None] = "infer",
    engine: Optional[str] = None,
    encoding_candidates: Optional[List[str]] = None,
    on_bad_lines: str = "skip",
    parse_dates: Optional[Union[List[str], Dict[str, str]]] = None,
    quotechar: Optional[str] = None,
    escapechar: Optional[str] = None,
    na_values: Optional[Sequence[str]] = None,
    low_memory: bool = False,
    storage_options: Optional[Dict[str, str]] = None,
) -> Iterator[pd.DataFrame]:
    """
    Attempt to create a chunk iterator with multiple encodings and engine fallbacks.
    
    CSV only - Parquet files are explicitly rejected.
    """
    # Reject Parquet files immediately
    path_str = str(path)
    if path_str.lower().endswith('.parquet'):
        raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {Path(path_str).name}")
    
    if engine is None:
        engine = _choose_engine("pyarrow")  # try pyarrow first, fall back to 'c'

    if encoding_candidates is None:
        # UTF-8 first; fall back to BOM and then Latin-1 (tolerant)
        encoding_candidates = ["utf-8", "utf-8-sig", "latin-1"]

    last_error = None
    for enc in encoding_candidates:
        try:
            it = pd.read_csv(
                path,
                chunksize=chunksize,
                usecols=usecols,
                dtype=dtypes,
                encoding=enc,
                delimiter=delimiter,
                compression=compression,
                engine=engine,
                on_bad_lines=on_bad_lines,  # skip malformed lines safely
                parse_dates=parse_dates,
                quotechar=quotechar,
                escapechar=escapechar,
                na_values=na_values,
                low_memory=low_memory,
                storage_options=storage_options,
                iterator=True,  # create TextFileReader
            )
            # Peek one chunk to validate the setup (and yield it)
            first = next(it, None)
            if first is None:
                # Empty file — yield nothing but don't error
                return iter(())

            # Build a generator that yields the peeked chunk then the rest
            def _gen():
                yield first
                for chunk in it:
                    yield chunk

            return _gen()
        except Exception as e:
            last_error = e
            # Try again with next encoding; if pyarrow engine failed, also try 'c' once.
            if engine == "pyarrow":
                try:
                    engine = "c"
                    it = pd.read_csv(
                        path,
                        chunksize=chunksize,
                        usecols=usecols,
                        dtype=dtypes,
                        encoding=enc,
                        delimiter=delimiter,
                        compression=compression,
                        engine=engine,
                        on_bad_lines=on_bad_lines,
                        parse_dates=parse_dates,
                        quotechar=quotechar,
                        escapechar=escapechar,
                        na_values=na_values,
                        low_memory=low_memory,
                        storage_options=storage_options,
                        iterator=True,
                    )
                    first = next(it, None)
                    if first is None:
                        return iter(())

                    def _gen2():
                        yield first
                        for chunk in it:
                            yield chunk

                    return _gen2()
                except Exception as e2:
                    last_error = e2
                    engine = "c"  # keep fallback for subsequent tries
                    continue
            else:
                continue

    # If all attempts failed, re-raise the most recent error with context
    raise RuntimeError(
        f"Failed to open CSV '{path}' with tried encodings {encoding_candidates} "
        f"and engine fallbacks. Last error: {last_error}"
    )


def read_csv_chunks(
    path: str,
    chunksize: int = 250_000,
    usecols: Optional[Sequence[str]] = None,
    dtypes: Optional[Dict[str, str]] = None,
    *,
    delimiter: Optional[str] = None,
    compression: Union[str, None] = "infer",
    parse_dates: Optional[Union[List[str], Dict[str, str]]] = None,
    quotechar: Optional[str] = None,
    escapechar: Optional[str] = None,
    na_values: Optional[Sequence[str]] = None,
    low_memory: bool = False,
    storage_options: Optional[Dict[str, str]] = None,
) -> Iterator[pd.DataFrame]:
    """
    Public API: robust chunked CSV iterator with encoding/engine fallbacks and sane defaults.
    
    CSV only - Parquet files are explicitly rejected.
    
    Args:
        path: Path to CSV file (local or remote: s3://, gs://, http(s)://)
        chunksize: Number of rows per chunk (default: 250,000)
        usecols: Optional list of column names to read (speeds up I/O)
        dtypes: Optional dict of column name -> dtype mappings
        delimiter: Optional delimiter character
        compression: Compression type ('infer', 'gzip', 'bz2', etc.) or None
        parse_dates: Columns to parse as dates
        quotechar: Quote character
        escapechar: Escape character
        na_values: Additional strings to recognize as NA/NaN
        low_memory: Use low memory mode (slower but uses less memory)
        storage_options: Options for remote storage (s3, gs, etc.)
    
    Yields:
        DataFrame chunks
    
    Raises:
        FileNotFoundError: If file doesn't exist (for local paths)
        ValueError: If file is Parquet (not supported)
        RuntimeError: If all encoding/engine attempts fail
    """
    # Enhanced file existence check for local paths
    path_str = str(path)
    if not path_str.startswith(("s3://", "gs://", "http://", "https://")):
        if not os.path.exists(path_str):
            raise FileNotFoundError(f"CSV file not found: {path_str}")
        # Additional validation: check if it's actually a file
        if not os.path.isfile(path_str):
            raise ValueError(f"Path exists but is not a file: {path_str}")

    warnings.simplefilter("ignore", category=FutureWarning)

    return _try_read_csv(
        path,
        chunksize=chunksize,
        usecols=usecols,
        dtypes=dtypes,
        delimiter=delimiter,
        compression=compression,
        parse_dates=parse_dates,
        quotechar=quotechar,
        escapechar=escapechar,
        na_values=na_values,
        low_memory=low_memory,
        storage_options=storage_options,
    )


# ----------------------------
# Numerics: Streaming Stats (Welford, chunk-merge)
# ----------------------------

def _coerce_numeric_array(series: pd.Series) -> np.ndarray:
    """
    Coerce to numeric float array, safely handling objects/strings/NaNs/inf.
    Non-parsable entries become NaN and are dropped by caller.
    """
    x = pd.to_numeric(series, errors="coerce")
    # return raw numpy for speed
    return x.to_numpy(dtype=float, copy=False)


def _batch_stats(x: np.ndarray) -> Tuple[int, float, float]:
    """
    Compute (n, mean, M2) for a numeric array ignoring NaNs.
    M2 is the sum of squared deviations: sum((xi - mean)^2)
    """
    if x.size == 0:
        return 0, 0.0, 0.0
    # Drop NaNs
    x = x[~np.isnan(x)]
    n = x.size
    if n == 0:
        return 0, 0.0, 0.0
    mean = float(np.mean(x))
    # var * n  (population M2; ddof=0)
    M2 = float(np.var(x, ddof=0) * n)
    return n, mean, M2


def _merge_stats(n1: int, mean1: float, M2_1: float, n2: int, mean2: float, M2_2: float) -> Tuple[int, float, float]:
    """
    Merge two (n, mean, M2) accumulators (Chan et al., 1979).
    Numerically stable for large datasets.
    """
    if n1 == 0:
        return n2, mean2, M2_2
    if n2 == 0:
        return n1, mean1, M2_1
    n = n1 + n2
    delta = mean2 - mean1
    mean = mean1 + delta * (n2 / n)
    M2 = M2_1 + M2_2 + delta * delta * (n1 * n2 / n)
    return n, mean, M2


def _safe_min_max_sum(x: np.ndarray) -> Tuple[Optional[float], Optional[float], float, int]:
    """
    Compute min, max, sum, null_count ignoring NaNs. Returns (min, max, sum, nulls_in_input).
    """
    nulls = int(np.isnan(x).sum())
    x = x[~np.isnan(x)]
    if x.size == 0:
        return None, None, 0.0, nulls
    return float(np.min(x)), float(np.max(x)), float(np.sum(x)), nulls


def incremental_numeric_profile(
    path: str,
    numeric_cols: Optional[Sequence[str]] = None,
    *,
    chunksize: int = 250_000,
    usecols: Optional[Sequence[str]] = None,
    dtypes: Optional[Dict[str, str]] = None,
    delimiter: Optional[str] = None,
    parse_dates: Optional[Union[List[str], Dict[str, str]]] = None,
    progress_cb: Optional[Callable[[int], None]] = None,
    min_numeric_ratio: float = 0.5,
) -> Dict[str, Dict[str, Union[int, float, None]]]:
    """
    Stream a CSV and compute robust numeric stats per-column:
      count, mean, std (population), min, max, sum, nulls

    - If numeric_cols is None, the first chunk is used to infer numeric-like columns.
    - Uses Welford + chunk-merge for numerical stability and low memory.
    - Never materializes the full dataset.
    - CSV only - Parquet files are explicitly rejected.

    Args:
        path: Path to CSV file (local or remote)
        numeric_cols: Optional list of column names to profile. If None, inferred from first chunk.
        chunksize: Number of rows per chunk (default: 250,000)
        usecols: Optional list of column names to read (speeds up I/O)
        dtypes: Optional dict of column name -> dtype mappings
        delimiter: Optional delimiter character
        parse_dates: Columns to parse as dates
        progress_cb: Optional callback function(rows_processed) for progress updates
        min_numeric_ratio: Minimum ratio of numeric values to consider a column numeric (default: 0.5)

    Returns:
        Dict mapping column name to stats dict:
        {
            column_name: {
                "count": int,      # Number of non-null numeric values
                "mean": float,     # Mean value (NaN if count=0)
                "std": float,       # Population std dev (NaN if count=0)
                "min": float | None, # Minimum value (None if count=0)
                "max": float | None, # Maximum value (None if count=0)
                "sum": float,       # Sum of values
                "nulls": int        # Number of null/NaN values
            }
        }

    Raises:
        ValueError: If path is a Parquet file (not supported)
        RuntimeError: If CSV cannot be read with any encoding/engine
        FileNotFoundError: If local file doesn't exist
    """
    # Reject Parquet files immediately
    path_str = str(path)
    if path_str.lower().endswith('.parquet'):
        raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {Path(path_str).name}")
    
    # Build chunk iterator
    it = read_csv_chunks(
        path,
        chunksize=chunksize,
        usecols=usecols if usecols is not None else None,
        dtypes=dtypes,
        delimiter=delimiter,
        parse_dates=parse_dates,
        low_memory=False,
    )

    # Initialize accumulators per column
    totals: Dict[str, Dict[str, Union[int, float, None]]] = {}
    n_acc: Dict[str, int] = {}
    mean_acc: Dict[str, float] = {}
    M2_acc: Dict[str, float] = {}
    min_acc: Dict[str, Optional[float]] = {}
    max_acc: Dict[str, Optional[float]] = {}
    sum_acc: Dict[str, float] = {}
    null_acc: Dict[str, int] = {}

    processed_rows = 0
    first_chunk = True

    try:
        for chunk in it:
            processed_rows += len(chunk.index)

            # Infer numeric columns on first chunk if needed
            if first_chunk:
                if numeric_cols is None:
                    # Consider columns numeric if at least min_numeric_ratio of non-null values can be coerced
                    inferred = []
                    for col in chunk.columns:
                        coerced = pd.to_numeric(chunk[col], errors="coerce")
                        # ratio of non-null numeric values among all non-null values
                        non_null = chunk[col].notna().sum()
                        if non_null == 0:
                            continue
                        numeric_non_null = coerced.notna().sum()
                        if numeric_non_null / max(non_null, 1) >= min_numeric_ratio:
                            inferred.append(col)
                    numeric_cols = inferred

                # Initialize per-column accumulators
                for c in (numeric_cols or []):
                    n_acc.setdefault(c, 0)
                    mean_acc.setdefault(c, 0.0)
                    M2_acc.setdefault(c, 0.0)
                    min_acc.setdefault(c, None)
                    max_acc.setdefault(c, None)
                    sum_acc.setdefault(c, 0.0)
                    null_acc.setdefault(c, 0)
                first_chunk = False

                # If still nothing to profile, bail with empty result
                if not numeric_cols:
                    return {}

            # Process numeric columns for this chunk
            for c in numeric_cols:
                arr = _coerce_numeric_array(chunk[c])
                # Track nulls (before dropping NaN)
                _min, _max, _sum, _nulls = _safe_min_max_sum(arr)
                null_acc[c] += _nulls

                # Batch stats on non-NaN values
                if arr.size - _nulls <= 0:
                    # nothing numeric in this chunk for c
                    continue
                n2, mean2, M2_2 = _batch_stats(arr)

                # Merge into global accumulators
                n1, mean1, M2_1 = n_acc[c], mean_acc[c], M2_acc[c]
                n, mean, M2 = _merge_stats(n1, mean1, M2_1, n2, mean2, M2_2)
                n_acc[c], mean_acc[c], M2_acc[c] = n, mean, M2

                # Merge min/max/sum
                if _min is not None:
                    min_acc[c] = _min if min_acc[c] is None else min(min_acc[c], _min)
                if _max is not None:
                    max_acc[c] = _max if max_acc[c] is None else max(max_acc[c], _max)
                sum_acc[c] += _sum

            if progress_cb:
                # Report rows processed so far
                progress_cb(processed_rows)

    except StopIteration:
        # Normal end of iteration - no problem
        pass
    except Exception as e:
        # Re-raise with better context
        raise RuntimeError(f"Error processing CSV '{path}' at row {processed_rows}: {e}") from e

    # Finalize results
    results: Dict[str, Dict[str, Union[int, float, None]]] = {}
    for c in (numeric_cols or []):
        n = n_acc.get(c, 0)
        if n == 0:
            results[c] = {
                "count": 0,
                "mean": math.nan,
                "std": math.nan,
                "min": None,
                "max": None,
                "sum": 0.0,
                "nulls": null_acc.get(c, 0),
            }
            continue
        variance = (M2_acc[c] / n) if n > 0 else math.nan  # population variance (ddof=0)
        std = math.sqrt(variance) if variance >= 0 else math.nan
        results[c] = {
            "count": n,
            "mean": mean_acc[c],
            "std": std,
            "min": min_acc[c],
            "max": max_acc[c],
            "sum": sum_acc[c],
            "nulls": null_acc.get(c, 0),
        }

    return results


# ----------------------------
# Convenience: File size estimation
# ----------------------------

def estimate_file_info(path: str) -> Dict[str, Union[int, float, str]]:
    """
    Estimate basic file information without reading the entire file.
    
    CSV only - Parquet files are explicitly rejected.
    
    Args:
        path: Path to CSV file
    
    Returns:
        Dict with file size, estimated row count (from first chunk), and other metadata
    """
    path_str = str(path)
    if path_str.lower().endswith('.parquet'):
        raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {Path(path_str).name}")
    
    if not path_str.startswith(("s3://", "gs://", "http://", "https://")):
        if not os.path.exists(path_str):
            raise FileNotFoundError(f"CSV file not found: {path_str}")
        
        stat = os.stat(path_str)
        file_size_bytes = stat.st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
    else:
        # Remote file - cannot get size easily without reading
        file_size_bytes = -1
        file_size_mb = -1.0
    
    # Read first chunk to estimate rows
    try:
        it = read_csv_chunks(path_str, chunksize=10000)
        first_chunk = next(it, None)
        if first_chunk is not None:
            estimated_rows = len(first_chunk)
            num_columns = len(first_chunk.columns)
        else:
            estimated_rows = 0
            num_columns = 0
    except Exception:
        estimated_rows = -1
        num_columns = -1
    
    return {
        "file_size_bytes": file_size_bytes,
        "file_size_mb": round(file_size_mb, 2) if file_size_mb >= 0 else -1.0,
        "estimated_rows": estimated_rows,
        "num_columns": num_columns,
        "is_remote": path_str.startswith(("s3://", "gs://", "http://", "https://")),
    }


# ----------------------------
# Example usage
# ----------------------------

if __name__ == "__main__":
    # Example usage:
    # stats = incremental_numeric_profile("big.csv", numeric_cols=None, chunksize=200_000)
    # print(stats)
    pass

