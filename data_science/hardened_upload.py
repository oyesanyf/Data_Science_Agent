"""
Hardened file upload handler with security and stability measures.
"""
import os
import re
import csv
import io
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# Security constants
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "100")) * 1024 * 1024  # 100MB default
ALLOWED_MIME_TYPES = {
    'text/csv', 'text/plain', 'application/csv', 'application/octet-stream',
    'text/tab-separated-values', 'application/vnd.ms-excel'
}
ALLOWED_EXTENSIONS = {'.csv', '.tsv', '.txt', '.data'}

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other security issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    if not filename:
        return "uploaded_file.csv"
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Decode URL encoding
    filename = unquote(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure it has an extension
    if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        filename += '.csv'
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename or "uploaded_file.csv"

def validate_mime_type(mime_type: str) -> bool:
    """
    Validate MIME type against allowlist.
    
    Args:
        mime_type: MIME type to validate
        
    Returns:
        True if allowed, False otherwise
    """
    if not mime_type:
        return False
    
    return mime_type.lower() in ALLOWED_MIME_TYPES

def detect_csv_delimiter(data: bytes, sample_size: int = 1024) -> str:
    """
    Detect CSV delimiter from data sample.
    
    Args:
        data: CSV data bytes
        sample_size: Size of sample to analyze
        
    Returns:
        Detected delimiter
    """
    try:
        # Take a sample of the data
        sample = data[:sample_size].decode('utf-8', errors='ignore')
        
        # Try common delimiters
        delimiters = [',', '\t', ';', '|']
        delimiter_counts = {}
        
        for delimiter in delimiters:
            try:
                reader = csv.Sniffer().sniff(sample, delimiters=delimiter)
                delimiter_counts[delimiter] = reader.delimiter
            except:
                continue
        
        # Return most common delimiter or default to comma
        if delimiter_counts:
            return max(delimiter_counts.values(), key=list(delimiter_counts.values()).count)
        
        return ','
        
    except Exception:
        return ','  # Default fallback

def validate_csv_structure(data: bytes, max_rows: int = 1000) -> Tuple[bool, Optional[str]]:
    """
    Validate CSV structure and detect issues.
    
    Args:
        data: CSV data bytes
        max_rows: Maximum rows to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Decode with multiple encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        decoded_data = None
        
        for encoding in encodings:
            try:
                decoded_data = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if decoded_data is None:
            return False, "Could not decode file with any supported encoding"
        
        # Detect delimiter
        delimiter = detect_csv_delimiter(data)
        
        # Parse CSV
        reader = csv.reader(io.StringIO(decoded_data), delimiter=delimiter)
        rows = list(reader)
        
        if not rows:
            return False, "File appears to be empty"
        
        # Check for reasonable structure
        if len(rows) < 2:
            return False, "File must have at least a header and one data row"
        
        # Check for consistent column count
        header_cols = len(rows[0])
        if header_cols == 0:
            return False, "Header row appears to be empty"
        
        # Check first few rows for consistency
        for i, row in enumerate(rows[1:min(10, len(rows))]):
            if len(row) != header_cols:
                return False, f"Row {i+2} has {len(row)} columns, expected {header_cols}"
        
        return True, None
        
    except Exception as e:
        return False, f"CSV validation error: {str(e)}"

def process_upload_safely(
    file_data: bytes,
    filename: str,
    mime_type: str,
    max_size: int = MAX_FILE_SIZE
) -> Dict[str, Any]:
    """
    Process file upload with security and stability measures.
    
    Args:
        file_data: File data bytes
        filename: Original filename
        mime_type: MIME type
        max_size: Maximum file size
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Security checks
        if len(file_data) > max_size:
            return {
                "success": False,
                "error": f"File too large: {len(file_data)} bytes (max: {max_size})",
                "error_type": "file_too_large"
            }
        
        if not validate_mime_type(mime_type):
            return {
                "success": False,
                "error": f"Unsupported MIME type: {mime_type}",
                "error_type": "invalid_mime_type"
            }
        
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        
        # Validate CSV structure
        is_valid, error_msg = validate_csv_structure(file_data)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg,
                "error_type": "invalid_csv"
            }
        
        # Create safe output path
        upload_dir = Path(os.getenv("UPLOAD_ROOT", "uploads"))
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename to prevent conflicts
        import time
        timestamp = int(time.time() * 1000)
        name, ext = os.path.splitext(safe_filename)
        unique_filename = f"{timestamp}_{name}{ext}"
        
        output_path = upload_dir / unique_filename
        
        # Write file safely
        with open(output_path, 'wb') as f:
            f.write(file_data)
        
        return {
            "success": True,
            "filename": unique_filename,
            "path": str(output_path),
            "size": len(file_data),
            "mime_type": mime_type,
            "original_filename": filename
        }
        
    except Exception as e:
        logger.error(f"Upload processing error: {e}")
        return {
            "success": False,
            "error": f"Processing error: {str(e)}",
            "error_type": "processing_error"
        }
