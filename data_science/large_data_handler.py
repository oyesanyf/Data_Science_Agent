"""
Large Dataset Handler - Streamed Uploads, No Size Limits
Handles GB+ files without memory spikes.
Parquet conversion is DISABLED - CSV only.
"""

import os
import re
import time
import base64
import binascii
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Conditional imports for Parquet/Arrow
try:
    import pyarrow as pa
    import pyarrow.csv as pv
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False

from .large_data_config import (
    UPLOAD_ROOT,
    UPLOAD_CHUNK_MB,
    PARQUET_ROWGROUP_MB,
    MAX_FILENAME_LENGTH,
    ALLOWED_EXTENSIONS,
    LOG_ABSOLUTE_PATHS
)

logger = logging.getLogger(__name__)


# ============================================================================
# Safe Filename Handling
# ============================================================================

def _safe_name(name: str, default: str = "uploaded.csv", maxlen: int = None) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        name: Original filename
        default: Default name if input is invalid
        maxlen: Maximum filename length (default from config)
    
    Returns:
        Sanitized filename
    """
    if maxlen is None:
        maxlen = MAX_FILENAME_LENGTH
    
    # Remove any path components (security)
    name = os.path.basename(name or default)
    
    # Replace unsafe characters with underscores
    base = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    
    # Ensure length constraint
    if len(base) > maxlen:
        # Preserve extension if possible
        ext_parts = base.rsplit('.', 1)
        if len(ext_parts) == 2:
            name_part, ext_part = ext_parts
            max_name_len = maxlen - len(ext_part) - 1
            base = f"{name_part[:max_name_len]}.{ext_part}"
        else:
            base = base[:maxlen]
    
    return base or default


def _validate_extension(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = Path(filename).suffix.lower()
    # Handle double extensions like .csv.gz
    if ext == '.gz' or ext == '.zst':
        double_ext = ''.join(Path(filename).suffixes[-2:]).lower()
        return double_ext in ALLOWED_EXTENSIONS
    return ext in ALLOWED_EXTENSIONS


# ============================================================================
# Streamed File Upload (No Memory Spike, No Size Limit)
# ============================================================================

def save_upload(
    base64_or_bytes,
    original_name: Optional[str] = None,
    buf_mb: Optional[int] = None
) -> Dict[str, Any]:
    """
    Save uploaded file with streaming (no memory spike).
    
    Args:
        base64_or_bytes: File content (base64 string or bytes)
        original_name: Original filename
        buf_mb: Buffer size in MB (default from config)
    
    Returns:
        Dictionary with file_id and metadata (NO absolute paths)
    """
    if buf_mb is None:
        buf_mb = UPLOAD_CHUNK_MB
    
    # Ensure upload directory exists
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    
    # [FIX] Check if identical file already exists using content hash
    # This prevents creating duplicate files with different timestamps
    import hashlib
    
    # Prepare data for hashing (convert to bytes if needed)
    data_for_hash = base64_or_bytes
    if isinstance(data_for_hash, str):
        try:
            data_for_hash = base64.b64decode(data_for_hash, validate=True)
        except binascii.Error:
            data_for_hash = data_for_hash.encode("utf-8", "ignore")
    
    # Calculate content hash
    content_hash = hashlib.sha256(data_for_hash).hexdigest()[:16]  # Use first 16 chars of hash
    logger.info(f"[UPLOAD] Content hash: {content_hash}")
    
    # Check if file with same content already exists
    safe_filename = _safe_name(original_name)
    existing_files = list(UPLOAD_ROOT.glob(f"*_{safe_filename}"))
    
    for existing_file in existing_files:
        try:
            # Compare file size first (fast check)
            if existing_file.stat().st_size == len(data_for_hash):
                # Calculate hash of existing file
                with open(existing_file, "rb") as f:
                    existing_hash = hashlib.sha256(f.read()).hexdigest()[:16]
                
                if existing_hash == content_hash:
                    logger.info(f"[UPLOAD] Identical file already exists: {existing_file.name}, reusing it")
                    return {
                        "status": "success",
                        "file_id": existing_file.name,
                        "bytes": existing_file.stat().st_size,
                        "throughput_mb_s": 0,  # No actual upload
                        "message": f"File already exists: {existing_file.name}",
                        "reused": True
                    }
        except Exception as e:
            logger.warning(f"[UPLOAD] Error checking existing file {existing_file}: {e}")
            continue
    
    # No duplicate found, create new file with timestamp
    ts = int(time.time())
    fname = f"{ts}_{safe_filename}"
    fpath = UPLOAD_ROOT / fname
    logger.info(f"[UPLOAD] Creating new file: {fname}")
    
    # Validate extension
    if not _validate_extension(safe_filename):
        logger.warning(f"File extension not in allowed list: {safe_filename}")
        # Still proceed, but log the warning
    
    # Stream write to disk
    bufsize = buf_mb * 1024 * 1024
    bytes_written = 0
    start_time = time.time()
    
    try:
        with open(fpath, "wb", buffering=bufsize) as f:
            # Handle both string (base64) and bytes input
            data = base64_or_bytes
            
            if isinstance(data, str):
                # Try base64 decode first
                try:
                    decoded = base64.b64decode(data, validate=True)
                    f.write(decoded)
                    bytes_written = len(decoded)
                except binascii.Error:
                    # Not base64, treat as UTF-8 text
                    encoded = data.encode("utf-8", "ignore")
                    f.write(encoded)
                    bytes_written = len(encoded)
            else:
                # Bytes input - try base64 decode first
                try:
                    decoded = base64.b64decode(data, validate=True)
                    f.write(decoded)
                    bytes_written = len(decoded)
                except binascii.Error:
                    # Already raw bytes
                    f.write(data)
                    bytes_written = len(data)
        
        elapsed = time.time() - start_time
        throughput_mb = (bytes_written / 1024 / 1024) / max(elapsed, 0.001)
        
        # Log success (PII-safe, no absolute paths unless debug)
        log_msg = {
            "event": "upload_success",
            "file_id": fname,
            "bytes": bytes_written,
            "elapsed_s": round(elapsed, 2),
            "throughput_mb_s": round(throughput_mb, 2)
        }
        
        if LOG_ABSOLUTE_PATHS:
            log_msg["path"] = str(fpath)
        
        logger.info(json.dumps(log_msg))
        
        # [CRITICAL FIX] Convert Parquet to CSV automatically
        if fpath.suffix.lower() == '.parquet':
            logger.info(f"[UPLOAD] Parquet file detected: {fname}, converting to CSV...")
            try:
                import pandas as pd
                
                # Read parquet
                df = pd.read_parquet(fpath)
                logger.info(f"[UPLOAD] Read parquet file: {len(df)} rows, {len(df.columns)} columns")
                
                # Create CSV filename
                csv_filename = fname.replace('.parquet', '.csv')
                csv_path = UPLOAD_ROOT / csv_filename
                
                # Save as CSV
                df.to_csv(csv_path, index=False)
                logger.info(f"[UPLOAD] Saved CSV: {csv_path} ({csv_path.stat().st_size} bytes)")
                
                # Delete original parquet file
                try:
                    fpath.unlink()
                    logger.info(f"[UPLOAD] Deleted original parquet file: {fname}")
                except Exception as unlink_err:
                    logger.error(f"[UPLOAD] Failed to delete parquet file {fname}: {unlink_err}")
                    # Continue anyway - CSV is created
                
                logger.info(f"[UPLOAD] ✓ Converted {fname} → {csv_filename}")
                
                # Fix original_name if it has .parquet extension
                csv_original_name = original_name
                if original_name and original_name.lower().endswith('.parquet'):
                    csv_original_name = original_name[:-8] + '.csv'  # Replace .parquet with .csv
                elif not original_name or not original_name.lower().endswith('.csv'):
                    csv_original_name = csv_filename
                
                return {
                    "file_id": csv_filename,  # Return CSV filename
                    "original_name": csv_original_name,
                    "bytes": csv_path.stat().st_size,
                    "elapsed_s": round(elapsed, 2),
                    "throughput_mb_s": round(throughput_mb, 2),
                    "converted_from": "parquet"
                }
            except Exception as e:
                logger.error(f"[UPLOAD] Failed to convert Parquet to CSV: {e}", exc_info=True)
                # Return error - parquet file remains
                return {
                    "file_id": fname,
                    "original_name": original_name or safe_filename,
                    "bytes": bytes_written,
                    "elapsed_s": round(elapsed, 2),
                    "throughput_mb_s": round(throughput_mb, 2),
                    "error": f"Parquet files are not supported. Conversion failed: {str(e)}"
                }
        
        # Return file_id only (no absolute paths exposed)
        return {
            "file_id": fname,
            "original_name": original_name or safe_filename,
            "bytes": bytes_written,
            "elapsed_s": round(elapsed, 2),
            "throughput_mb_s": round(throughput_mb, 2)
        }
    
    except Exception as e:
        logger.error(f"Upload failed for {fname}: {e}")
        # Clean up partial file
        if fpath.exists():
            fpath.unlink()
        raise


# ============================================================================
# File ID Resolution (Internal Use Only)
# ============================================================================

def resolve_file_id(file_id: str) -> Optional[Path]:
    """
    Resolve file_id to actual filesystem path (internal use only).
    
    Args:
        file_id: File identifier returned from save_upload()
    
    Returns:
        Path object or None if not found
    """
    fpath = UPLOAD_ROOT / file_id
    return fpath if fpath.exists() else None


def list_data_files() -> Dict[str, Dict[str, Any]]:
    """
    List all uploaded files (returns file_ids, not paths).
    
    Returns:
        Dictionary mapping file_id to metadata
    """
    files = {}
    
    for fpath in UPLOAD_ROOT.glob("*"):
        if fpath.is_file():
            stat = fpath.stat()
            files[fpath.name] = {
                "file_id": fpath.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified": stat.st_mtime,
                "extension": fpath.suffix
            }
    
    return files


# ============================================================================
# CSV to Parquet Conversion (DISABLED - CSV only)
# ============================================================================

def csv_to_parquet_stream(
    csv_path: Path,
    parquet_path: Optional[Path] = None,
    row_group_mb: Optional[int] = None
) -> Dict[str, Any]:
    """
    DISABLED: Parquet conversion is disabled. Only CSV files are supported.
    
    Args:
        csv_path: Path to CSV file (ignored)
        parquet_path: Output Parquet path (ignored)
        row_group_mb: Row group size in MB (ignored)
    
    Returns:
        Dictionary with skipped status
    """
    # Parquet support disabled - CSV only
    logger.debug(f"Parquet conversion disabled - skipping {csv_path}")
    return {"status": "skipped", "reason": "parquet_disabled"}
    
    # All conversion logic removed - Parquet disabled


def write_schema_stats(parquet_path: Path, meta_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    DISABLED: Parquet support is disabled. Only CSV files are supported.
    
    Args:
        parquet_path: Path to Parquet file (ignored)
        meta_path: Output metadata path (ignored)
    
    Returns:
        Dictionary with skipped status
    """
    # Parquet support disabled - CSV only
    logger.debug(f"Parquet schema stats disabled - skipping {parquet_path}")
    return {"status": "skipped", "reason": "parquet_disabled"}


# ============================================================================
# Automatic CSV→Parquet on First Touch
# ============================================================================

def auto_convert_csv_to_parquet(file_id: str) -> Optional[str]:
    """
    DISABLED: Parquet conversion is disabled. Only CSV files are supported.
    
    Args:
        file_id: File identifier (ignored)
    
    Returns:
        None (always - conversion disabled)
    """
    # Parquet support disabled - CSV only
    logger.debug(f"Parquet conversion disabled - skipping {file_id}")
    return None


# ============================================================================
# Utility Functions
# ============================================================================

def get_file_info(file_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a file."""
    fpath = resolve_file_id(file_id)
    if not fpath or not fpath.exists():
        return None
    
    stat = fpath.stat()
    info = {
        "file_id": file_id,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / 1024 / 1024, 2),
        "modified": stat.st_mtime,
        "extension": fpath.suffix,
        "is_csv": fpath.suffix.lower() in ['.csv', '.txt'],
        "is_parquet": fpath.suffix.lower() == '.parquet',
        "is_compressed": fpath.suffix.lower() in ['.gz', '.zst']
    }
    
    # Check for Parquet version
    if info["is_csv"]:
        parquet_path = fpath.with_suffix('.parquet')
        info["has_parquet_version"] = parquet_path.exists()
        if info["has_parquet_version"]:
            info["parquet_file_id"] = parquet_path.name
    
    return info


def cleanup_old_files(days: int = 30) -> int:
    """
    Clean up files older than specified days.
    
    Args:
        days: Files older than this many days will be deleted
    
    Returns:
        Number of files deleted
    """
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    deleted = 0
    
    for fpath in UPLOAD_ROOT.glob("*"):
        if fpath.is_file() and fpath.stat().st_mtime < cutoff_time:
            try:
                fpath.unlink()
                deleted += 1
                logger.info(f"Deleted old file: {fpath.name}")
            except Exception as e:
                logger.error(f"Failed to delete {fpath.name}: {e}")
    
    return deleted

