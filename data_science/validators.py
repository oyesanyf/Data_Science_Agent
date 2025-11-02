"""
Security validators for file uploads, ZIP extraction, and path traversal prevention.

All validators return (is_valid: bool, error_message: Optional[str]).
"""
from __future__ import annotations

import os
import zipfile
import uuid
from pathlib import Path
from typing import Tuple, List, Optional

from .config import Config


def validate_file_size(size_bytes: int) -> Tuple[bool, Optional[str]]:
    """Validate file size is within limits."""
    if size_bytes > Config.MAX_UPLOAD_BYTES:
        return False, f"File too large: {size_bytes:,} bytes (max: {Config.MAX_UPLOAD_BYTES:,})"
    return True, None


def validate_extension(filename: str) -> Tuple[bool, Optional[str]]:
    """Validate file extension is in allowlist."""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in Config.ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' not allowed. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"
    return True, None


def validate_safe_path(path: str) -> Tuple[bool, Optional[str]]:
    """Validate path doesn't contain traversal attacks or dangerous patterns."""
    # Normalize path
    normalized = path.replace("\\", "/")
    
    # Check for path traversal
    if normalized.startswith("/") or ".." in normalized or "\x00" in normalized:
        return False, f"Unsafe path detected: {path}"
    
    # Check for hidden files (optional - may want to allow)
    # if normalized.startswith("."):
    #     return False, f"Hidden files not allowed: {path}"
    
    return True, None


def validate_zip_member(member_name: str) -> Tuple[bool, Optional[str]]:
    """Validate ZIP member name is safe to extract."""
    # Check path safety
    is_safe, error = validate_safe_path(member_name)
    if not is_safe:
        return False, error
    
    # Check extension if it's a file
    if not member_name.endswith("/"):
        ext_valid, ext_error = validate_extension(member_name)
        if not ext_valid:
            return False, f"ZIP member has disallowed extension: {member_name}"
    
    return True, None


def safe_unzip(
    zip_path: str,
    dest_root: str,
    max_entries: Optional[int] = None,
    max_uncompressed: Optional[int] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Safely extract ZIP file with validation.
    
    Returns:
        (success: bool, extracted_dir: str, error_msg: Optional[str])
    """
    max_entries = max_entries or Config.MAX_ZIP_ENTRIES
    max_uncompressed = max_uncompressed or Config.MAX_ZIP_UNCOMPRESSED
    
    # Create unique extraction directory
    dest_dir = os.path.join(dest_root, f"unzipped_{uuid.uuid4().hex}")
    os.makedirs(dest_dir, mode=0o700, exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Validate ZIP integrity
            if zf.testzip() is not None:
                return False, dest_dir, "ZIP file is corrupted"
            
            infos = zf.infolist()
            
            # Check entry count
            if len(infos) > max_entries:
                return False, dest_dir, f"Too many ZIP entries: {len(infos)} (max: {max_entries})"
            
            # Check uncompressed size (zip bomb protection)
            total_uncompressed = 0
            for zi in infos:
                total_uncompressed += zi.file_size
                if total_uncompressed > max_uncompressed:
                    return False, dest_dir, f"ZIP uncompressed size too large: {total_uncompressed:,} (max: {max_uncompressed:,})"
            
            # Validate all member paths first
            unsafe_members = []
            for zi in infos:
                if Config.VALIDATE_ZIP_PATHS:
                    is_safe, error = validate_zip_member(zi.filename)
                    if not is_safe:
                        unsafe_members.append((zi.filename, error))
            
            if unsafe_members:
                errors = "\n".join([f"  - {name}: {err}" for name, err in unsafe_members[:5]])
                return False, dest_dir, f"Unsafe ZIP members detected:\n{errors}"
            
            # Extract files
            extracted_count = 0
            for zi in infos:
                if not zi.is_dir():
                    # Double-check extension
                    ext = os.path.splitext(zi.filename.lower())[1]
                    if ext not in Config.ALLOWED_EXTENSIONS:
                        continue  # Skip disallowed files silently
                    
                    # Extract safely
                    try:
                        zf.extract(zi, dest_dir)
                        extracted_count += 1
                    except Exception as e:
                        # Log but don't fail on single file errors
                        import logging
                        logging.warning(f"Failed to extract {zi.filename}: {e}")
                        continue
            
            return True, dest_dir, None
    
    except zipfile.BadZipFile:
        return False, dest_dir, "Invalid ZIP file"
    except Exception as e:
        return False, dest_dir, f"ZIP extraction error: {str(e)}"


def validate_csv_dimensions(rows: int, cols: int) -> Tuple[bool, Optional[str]]:
    """Validate CSV dimensions are within limits."""
    if rows > Config.MAX_CSV_ROWS:
        return False, f"Too many rows: {rows:,} (max: {Config.MAX_CSV_ROWS:,})"
    
    if cols > Config.MAX_CSV_COLS:
        return False, f"Too many columns: {cols} (max: {Config.MAX_CSV_COLS})"
    
    if rows * cols > Config.MAX_ROWS_COLS_PRODUCT:
        return False, f"Data too large: {rows:,} × {cols} = {rows*cols:,} (max product: {Config.MAX_ROWS_COLS_PRODUCT:,})"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace dangerous characters
    dangerous_chars = ['/', '\\', '..', '\x00', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename


def validate_mime_type(mime_type: str, expected_category: str) -> Tuple[bool, Optional[str]]:
    """
    Validate MIME type matches expected category.
    
    Args:
        mime_type: The MIME type from upload (untrusted)
        expected_category: Expected category ('image', 'text', 'application')
    
    Returns:
        (is_valid, error_message)
    """
    if not mime_type:
        return False, "Missing MIME type"
    
    mime_lower = mime_type.lower()
    
    if expected_category == "image":
        if not mime_lower.startswith("image/"):
            return False, f"Expected image MIME type, got: {mime_type}"
    elif expected_category == "text":
        if not (mime_lower.startswith("text/") or "csv" in mime_lower):
            return False, f"Expected text/CSV MIME type, got: {mime_type}"
    elif expected_category == "zip":
        if "zip" not in mime_lower:
            return False, f"Expected ZIP MIME type, got: {mime_type}"
    
    return True, None


def check_formula_injection(value: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a string contains formula injection patterns.
    
    Used when exporting to CSV/Excel to prevent formula execution.
    """
    if not value or not isinstance(value, str):
        return True, None
    
    dangerous_prefixes = ['=', '+', '-', '@', '\t', '\r']
    
    for prefix in dangerous_prefixes:
        if value.startswith(prefix):
            return False, f"Potential formula injection detected (starts with '{prefix}')"
    
    return True, None


def sanitize_for_export(value: str) -> str:
    """Sanitize string for safe CSV/Excel export."""
    if not value or not isinstance(value, str):
        return value
    
    dangerous_prefixes = ['=', '+', '-', '@', '\t', '\r']
    
    for prefix in dangerous_prefixes:
        if value.startswith(prefix):
            # Prefix with single quote to disable formula evaluation
            return "'" + value
    
    return value

