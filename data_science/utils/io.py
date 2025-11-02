from __future__ import annotations
from pathlib import Path
import pandas as pd


def read_dataset(path: str):
    """
    CSV-only dataset reader.
    
    Args:
        path: File path to read (must be CSV or TXT)
    
    Returns:
        DataFrame
    
    Raises:
        ValueError: If file type is not CSV or TXT
    """
    p = Path(path)
    suffix = p.suffix.lower()

    # Only allow CSV files
    if suffix not in (".csv", ".txt"):
        raise ValueError(f"Unsupported file type: {suffix}. Only CSV files are accepted.")

    try:
        # Try UTF-8 first, fallback to latin-1 for edge cases
        return pd.read_csv(p, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(p, encoding="latin-1", errors="replace")


def robust_read_table(path: str | Path, validate_only: bool = False) -> pd.DataFrame | bool:
    """
    CSV-only reader with encoding fallbacks and permissive parsing.
    
    Args:
        path: File path to read (must be CSV)
        validate_only: If True, just checks if file is readable (returns True/False)
    
    Returns:
        DataFrame if validate_only=False, bool if validate_only=True
    
    Raises:
        ValueError: If file is not CSV
    """
    p = Path(path)
    suffix = p.suffix.lower()
    
    # Reject Parquet files (CSV only)
    if suffix == ".parquet":
        if validate_only:
            return False
        raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. File: {p.name}")
    
    if validate_only:
        # Quick validation: just check if file exists and has reasonable structure
        try:
            if not p.exists():
                return False
            # For CSV, try to read just the header to validate structure
            pd.read_csv(p, nrows=0, low_memory=False, on_bad_lines="skip")
            return True
        except Exception:
            return False
    
    # CSV-family with encoding fallbacks + permissive parsing
    import re
    def _sanitize_column_names(columns):
        """Remove control characters and binary garbage from column names."""
        sanitized = []
        for col in columns:
            col_str = str(col)
            # Remove control characters (0x00-0x1F except tab, newline, carriage return)
            col_str = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', col_str)
            # Remove any non-printable characters beyond 0x7F that aren't valid unicode
            col_str = re.sub(r'[^\x20-\x7E\u00A0-\uFFFF]', '', col_str)
            # Strip and provide fallback
            col_str = col_str.strip() or f"column_{len(sanitized)}"
            sanitized.append(col_str)
        return sanitized
    
    try:
        df = pd.read_csv(p, low_memory=False, on_bad_lines="skip")
        df.columns = _sanitize_column_names(df.columns)
        return df
    except UnicodeDecodeError:
        for enc in ("utf-8-sig", "cp1252", "latin1"):
            try:
                df = pd.read_csv(p, low_memory=False, encoding=enc, on_bad_lines="skip")
                df.columns = _sanitize_column_names(df.columns)
                return df
            except Exception:
                pass
        # last resort: errors="replace" to avoid hard crash
        df = pd.read_csv(p, low_memory=False, encoding="utf-8", errors="replace", on_bad_lines="skip")
        df.columns = _sanitize_column_names(df.columns)
        return df
    except pd.errors.ParserError:
        # auto-separator + skip bad lines
        df = pd.read_csv(
            p, sep=None, engine="python", on_bad_lines="skip", low_memory=False
        )
        df.columns = _sanitize_column_names(df.columns)
        return df


