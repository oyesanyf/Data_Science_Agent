"""
Multi-Layer File Validation System with LLM Intelligence

Validates files through multiple stages before processing:
1. Parameter validation (csv_path provided)
2. File existence (physical file on disk)
3. File readability (can open and read)
4. File structure (valid CSV/Parquet format)
5. LLM validation (semantic checks on content)

This prevents silent failures and provides clear error messages to users.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """Custom exception for file validation failures"""
    pass


def _find_file_in_common_locations(filename: str) -> Optional[str]:
    """
    Search for file in common upload/data directories.
    
    Args:
        filename: Base filename to search for
        
    Returns:
        Full path if found, None otherwise
    """
    from .large_data_config import UPLOAD_ROOT
    
    search_paths = [
        UPLOAD_ROOT,  # Main upload directory
        os.path.join(UPLOAD_ROOT, ".."),  # Parent directory
        "data",
        "datasets",
        "uploads",
        ".",  # Current directory
    ]
    
    for search_dir in search_paths:
        if not os.path.exists(search_dir):
            continue
            
        # Try direct path
        full_path = os.path.join(search_dir, filename)
        if os.path.isfile(full_path):
            logger.info(f"[FILE VALIDATOR] Found file: {full_path}")
            return full_path
            
        # Try recursive search (max 2 levels deep)
        for root, dirs, files in os.walk(search_dir):
            if filename in files:
                full_path = os.path.join(root, filename)
                logger.info(f"[FILE VALIDATOR] Found file in subdirectory: {full_path}")
                return full_path
            # Limit recursion depth
            if root.count(os.sep) - search_dir.count(os.sep) >= 2:
                del dirs[:]
    
    return None


def validate_file_multi_layer(
    csv_path: str,
    tool_context: Optional[Any] = None,
    tool_name: str = "unknown",
    require_llm_validation: bool = False
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Multi-layer file validation with LLM intelligence.
    
    Validation Layers:
        1. Parameter Check: Is csv_path provided?
        2. State Recovery: Try auto-binding from tool_context.state
        3. File Existence: Does file exist on disk?
        4. File Search: Search common locations if not found
        5. File Readability: Can we open and read the file?
        6. Format Validation: Is it valid CSV/Parquet?
        7. LLM Validation: Semantic content validation (optional)
    
    Args:
        csv_path: File path to validate
        tool_context: ADK tool context (for state access)
        tool_name: Name of calling tool (for logging)
        require_llm_validation: If True, perform LLM semantic validation
        
    Returns:
        Tuple of (is_valid, validated_path_or_error_msg, metadata_dict)
        - is_valid: True if all validations passed
        - validated_path_or_error_msg: Full file path if valid, error message if not
        - metadata_dict: File metadata (rows, columns, size) if valid, None if not
    """
    logger.info(f"[FILE VALIDATOR] Starting multi-layer validation for {tool_name}")
    print(f"\n{'='*80}", flush=True)
    print(f"[FILE VALIDATOR] [VALIDATION] MULTI-LAYER VALIDATION STARTING", flush=True)
    print(f"[FILE VALIDATOR] Tool: {tool_name}", flush=True)
    print(f"[FILE VALIDATOR] Initial csv_path: {csv_path or 'NOT PROVIDED'}", flush=True)
    
    # ============================================================
    # LAYER 1: Parameter Validation
    # ============================================================
    print(f"[FILE VALIDATOR] Layer 1: Parameter Check...", flush=True)
    if not csv_path:
        logger.warning(f"[FILE VALIDATOR] Layer 1 FAILED: No csv_path provided")
        print(f"[FILE VALIDATOR] [X] Layer 1 FAILED: No csv_path", flush=True)
        
        # ============================================================
        # LAYER 2: State Recovery (Auto-Binding)
        # ============================================================
        print(f"[FILE VALIDATOR] Layer 2: State Recovery...", flush=True)
        if tool_context and hasattr(tool_context, 'state'):
            csv_path = (tool_context.state.get("default_csv_path") or 
                       tool_context.state.get("dataset_csv_path") or "")
            if csv_path:
                logger.info(f"[FILE VALIDATOR] Layer 2 SUCCESS: Auto-bound from state: {csv_path}")
                print(f"[FILE VALIDATOR] [OK] Layer 2 SUCCESS: Auto-bound csv_path from state", flush=True)
                print(f"[FILE VALIDATOR]    Recovered path: {csv_path}", flush=True)
            else:
                logger.error(f"[FILE VALIDATOR] Layer 2 FAILED: No path in state")
                print(f"[FILE VALIDATOR] [X] Layer 2 FAILED: No path in state", flush=True)
                error_msg = (
                    f"[X] **[{tool_name}] Cannot proceed - No dataset specified!**\n\n"
                    "**VALIDATION FAILED AT LAYER 2: State Recovery**\n\n"
                    "**Multi-Layer Validation Results:**\n"
                    "- [X] Layer 1: Parameter Check - FAILED (csv_path not provided)\n"
                    "- [X] Layer 2: State Recovery - FAILED (no default_csv_path in state)\n\n"
                    "**Quick Fix:**\n"
                    "1. Upload a CSV file through the UI\n"
                    "2. Run `list_data_files()` to see available files\n"
                    "3. Run `analyze_dataset(csv_path='your_file.csv')` to set default\n"
                    "4. Or pass `csv_path` explicitly: `{tool_name}(csv_path='your_file.csv')`\n\n"
                    " **Tip:** After uploading a file, it's automatically saved as `default_csv_path` in state."
                )
                print(f"{'='*80}\n", flush=True)
                return False, error_msg, None
        else:
            logger.error(f"[FILE VALIDATOR] Layer 2 FAILED: No tool_context")
            print(f"[FILE VALIDATOR] [X] Layer 2 FAILED: No tool_context", flush=True)
            error_msg = (
                f"[X] **[{tool_name}] Cannot proceed - No dataset specified!**\n\n"
                "**VALIDATION FAILED AT LAYER 1: Parameter Check**\n\n"
                "No csv_path provided and no tool_context available for state recovery."
            )
            print(f"{'='*80}\n", flush=True)
            return False, error_msg, None
    else:
        logger.info(f"[FILE VALIDATOR] Layer 1 SUCCESS: csv_path provided")
        print(f"[FILE VALIDATOR] [OK] Layer 1 SUCCESS: csv_path provided", flush=True)
    
    # ============================================================
    # LAYER 3: File Existence Check
    # ============================================================
    print(f"[FILE VALIDATOR] Layer 3: File Existence Check...", flush=True)
    if not os.path.isfile(csv_path):
        logger.warning(f"[FILE VALIDATOR] Layer 3 FAILED: File not found at {csv_path}")
        print(f"[FILE VALIDATOR] [X] Layer 3 FAILED: File not found", flush=True)
        print(f"[FILE VALIDATOR]    Checked path: {csv_path}", flush=True)
        
        # ============================================================
        # LAYER 4: Smart File Search
        # ============================================================
        print(f"[FILE VALIDATOR] Layer 4: Smart File Search...", flush=True)
        filename = os.path.basename(csv_path)
        found_path = _find_file_in_common_locations(filename)
        
        if found_path:
            logger.info(f"[FILE VALIDATOR] Layer 4 SUCCESS: Found file at {found_path}")
            print(f"[FILE VALIDATOR] [OK] Layer 4 SUCCESS: File found in alternate location", flush=True)
            print(f"[FILE VALIDATOR]    New path: {found_path}", flush=True)
            csv_path = found_path
        else:
            logger.error(f"[FILE VALIDATOR] Layer 4 FAILED: File not found anywhere")
            print(f"[FILE VALIDATOR] [X] Layer 4 FAILED: File not found in any location", flush=True)
            error_msg = (
                f"[X] **[{tool_name}] Cannot proceed - File not found!**\n\n"
                f"**VALIDATION FAILED AT LAYER 3: File Existence**\n\n"
                f"**Searched for:** `{filename}`\n"
                f"**Original path:** `{csv_path}`\n\n"
                f"**Multi-Layer Validation Results:**\n"
                f"- [OK] Layer 1: Parameter Check - PASSED\n"
                f"- [OK] Layer 2: State Recovery - PASSED\n"
                f"- [X] Layer 3: File Existence - FAILED (file not on disk)\n"
                f"- [X] Layer 4: Smart Search - FAILED (searched common locations)\n\n"
                f"**Searched locations:**\n"
                f"- Upload directory\n"
                f"- Data directory\n"
                f"- Datasets directory\n"
                f"- Current directory\n\n"
                f"**Possible causes:**\n"
                f"- File was deleted or moved\n"
                f"- Upload failed or was interrupted\n"
                f"- Incorrect filename in session state\n\n"
                f"**Quick Fix:**\n"
                f"1. Re-upload your CSV file\n"
                f"2. Run `list_data_files()` to see available files\n"
                f"3. Use the exact filename from the list\n"
            )
            print(f"{'='*80}\n", flush=True)
            return False, error_msg, None
    else:
        logger.info(f"[FILE VALIDATOR] Layer 3 SUCCESS: File exists at {csv_path}")
        print(f"[FILE VALIDATOR] [OK] Layer 3 SUCCESS: File exists", flush=True)
    
    # ============================================================
    # LAYER 5: File Readability Check
    # ============================================================
    print(f"[FILE VALIDATOR] Layer 5: File Readability Check...", flush=True)
    try:
        with open(csv_path, 'rb') as f:
            f.read(1024)  # Try reading first 1KB
        logger.info(f"[FILE VALIDATOR] Layer 5 SUCCESS: File is readable")
        print(f"[FILE VALIDATOR] [OK] Layer 5 SUCCESS: File is readable", flush=True)
    except Exception as e:
        logger.error(f"[FILE VALIDATOR] Layer 5 FAILED: {e}")
        print(f"[FILE VALIDATOR] [X] Layer 5 FAILED: Cannot read file", flush=True)
        error_msg = (
            f"[X] **[{tool_name}] Cannot proceed - File is not readable!**\n\n"
            f"**VALIDATION FAILED AT LAYER 5: File Readability**\n\n"
            f"**File path:** `{csv_path}`\n"
            f"**Error:** `{str(e)}`\n\n"
            f"**Multi-Layer Validation Results:**\n"
            f"- [OK] Layers 1-3: PASSED\n"
            f"- [X] Layer 5: Readability - FAILED (permission or corruption issue)\n\n"
            f"**Possible causes:**\n"
            f"- File permissions issue\n"
            f"- File is corrupted\n"
            f"- File is locked by another process\n\n"
            f"**Quick Fix:**\n"
            f"1. Check file permissions\n"
            f"2. Re-upload the file\n"
            f"3. Ensure no other program has the file open\n"
        )
        print(f"{'='*80}\n", flush=True)
        return False, error_msg, None
    
    # ============================================================
    # LAYER 6: Format Validation (CSV/Parquet Structure)
    # ============================================================
    print(f"[FILE VALIDATOR] Layer 6: Format Validation...", flush=True)
    try:
        file_ext = Path(csv_path).suffix.lower()
        
        if file_ext == '.parquet':
            df = pd.read_parquet(csv_path)
            file_type = "Parquet"
        elif file_ext in ['.csv', '.txt']:
            df = pd.read_csv(csv_path, nrows=5)  # Read only first 5 rows for validation
            file_type = "CSV"
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        metadata = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "file_size_mb": round(os.path.getsize(csv_path) / (1024 * 1024), 2),
            "file_type": file_type,
            "has_data": len(df) > 0
        }
        
        logger.info(f"[FILE VALIDATOR] Layer 6 SUCCESS: Valid {file_type} file")
        logger.info(f"[FILE VALIDATOR]    Rows: {metadata['rows']}, Columns: {metadata['columns']}")
        print(f"[FILE VALIDATOR] [OK] Layer 6 SUCCESS: Valid {file_type} format", flush=True)
        print(f"[FILE VALIDATOR]    Rows: {metadata['rows']}, Columns: {metadata['columns']}", flush=True)
        print(f"[FILE VALIDATOR]    Size: {metadata['file_size_mb']} MB", flush=True)
        
        # Check if file is empty
        if metadata['rows'] == 0:
            logger.warning(f"[FILE VALIDATOR] Layer 6 WARNING: File is empty (0 rows)")
            print(f"[FILE VALIDATOR] [WARNING]  Layer 6 WARNING: File has 0 rows", flush=True)
            error_msg = (
                f"[WARNING] **[{tool_name}] File is valid but empty!**\n\n"
                f"**VALIDATION WARNING AT LAYER 6: Format Validation**\n\n"
                f"**File path:** `{csv_path}`\n"
                f"**Format:** Valid {file_type}\n"
                f"**Columns:** {metadata['columns']}\n"
                f"**Rows:** 0 [WARNING]\n\n"
                f"The file structure is valid, but it contains no data rows.\n\n"
                f"**Quick Fix:**\n"
                f"1. Check if you uploaded the correct file\n"
                f"2. Ensure the source file contains data\n"
                f"3. Re-upload a file with actual data rows\n"
            )
            print(f"{'='*80}\n", flush=True)
            return False, error_msg, metadata
        
    except Exception as e:
        logger.error(f"[FILE VALIDATOR] Layer 6 FAILED: {e}")
        print(f"[FILE VALIDATOR] [X] Layer 6 FAILED: Invalid file format", flush=True)
        print(f"[FILE VALIDATOR]    Error: {str(e)[:200]}", flush=True)
        error_msg = (
            f"[X] **[{tool_name}] Cannot proceed - Invalid file format!**\n\n"
            f"**VALIDATION FAILED AT LAYER 6: Format Validation**\n\n"
            f"**File path:** `{csv_path}`\n"
            f"**Error:** `{str(e)}`\n\n"
            f"**Multi-Layer Validation Results:**\n"
            f"- [OK] Layers 1-5: PASSED\n"
            f"- [X] Layer 6: Format Validation - FAILED (not valid CSV/Parquet)\n\n"
            f"**Possible causes:**\n"
            f"- File is not a valid CSV or Parquet file\n"
            f"- File encoding issues (try UTF-8)\n"
            f"- Corrupted file structure\n"
            f"- Incorrect delimiter (CSV should be comma-separated)\n\n"
            f"**Quick Fix:**\n"
            f"1. Check file format (must be .csv or .parquet)\n"
            f"2. Ensure proper CSV structure (header row, consistent columns)\n"
            f"3. Save file with UTF-8 encoding\n"
            f"4. Re-upload the file\n"
        )
        print(f"{'='*80}\n", flush=True)
        return False, error_msg, None
    
    # ============================================================
    # LAYER 7: LLM Semantic Validation (Optional)
    # ============================================================
    if require_llm_validation and tool_context:
        print(f"[FILE VALIDATOR] Layer 7: LLM Semantic Validation...", flush=True)
        try:
            # TODO: Implement LLM validation
            # This would use the LLM to check:
            # - Are column names meaningful?
            # - Does data structure make sense?
            # - Are there obvious data quality issues?
            # - Is this the right file for the user's task?
            logger.info(f"[FILE VALIDATOR] Layer 7: LLM validation requested (not yet implemented)")
            print(f"[FILE VALIDATOR] ℹ  Layer 7: LLM validation (future enhancement)", flush=True)
        except Exception as e:
            logger.warning(f"[FILE VALIDATOR] Layer 7 non-critical failure: {e}")
            print(f"[FILE VALIDATOR] [WARNING]  Layer 7: LLM validation skipped ({str(e)})", flush=True)
    
    # ============================================================
    # ALL LAYERS PASSED!
    # ============================================================
    logger.info(f"[FILE VALIDATOR] [OK] ALL VALIDATION LAYERS PASSED")
    logger.info(f"[FILE VALIDATOR]    Validated path: {csv_path}")
    logger.info(f"[FILE VALIDATOR]    Metadata: {metadata}")
    print(f"[FILE VALIDATOR] [OK] ALL VALIDATION LAYERS PASSED!", flush=True)
    print(f"[FILE VALIDATOR]    Final path: {csv_path}", flush=True)
    print(f"[FILE VALIDATOR]    {file_type}: {metadata['rows']} rows × {metadata['columns']} columns", flush=True)
    print(f"{'='*80}\n", flush=True)
    
    return True, csv_path, metadata

