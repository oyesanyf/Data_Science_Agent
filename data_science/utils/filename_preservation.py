"""
Utility functions for preserving original filenames when tools modify CSV files.

This ensures that:
1. Only one file exists in the workspace at a time
2. After any tool modifies a file, it's renamed back to the original filename
3. The original file is backed up (not used, just kept as backup)
4. All tools follow the same pattern for consistency
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


def ensure_single_file_in_workspace(uploads_dir: str) -> int:
    """
    Ensure only ONE file exists in uploads directory by removing duplicates.
    Keeps the earliest file (by filename timestamp) and deletes all others.
    
    Args:
        uploads_dir: Path to the uploads directory
        
    Returns:
        Number of duplicate files deleted
    """
    if not os.path.exists(uploads_dir):
        return 0
    
    try:
        all_csvs = list(Path(uploads_dir).glob("*.csv"))
        # Exclude backup files
        all_csvs = [f for f in all_csvs if not f.name.endswith(".backup")]
        
        if len(all_csvs) <= 1:
            return 0  # No duplicates possible
        
        # Group by size (same size = likely duplicates)
        files_by_size = defaultdict(list)
        for csv_file in all_csvs:
            try:
                size = csv_file.stat().st_size
                files_by_size[size].append(csv_file)
            except Exception:
                continue
        
        # For each size group with multiple files, keep only earliest (by filename)
        total_deleted = 0
        for size, files_list in files_by_size.items():
            if len(files_list) > 1:
                # Sort by filename (earliest timestamp first)
                files_list.sort(key=lambda f: f.name)
                earliest = files_list[0]
                
                # Delete all duplicates except earliest
                for duplicate in files_list[1:]:
                    try:
                        duplicate.unlink()
                        total_deleted += 1
                        logger.info(f"[SINGLE FILE ENFORCEMENT] ✅ Deleted duplicate: {duplicate.name} (kept earliest: {earliest.name})")
                    except Exception as e:
                        logger.warning(f"[SINGLE FILE ENFORCEMENT] Could not delete duplicate {duplicate.name}: {e}")
        
        if total_deleted > 0:
            logger.info(f"[SINGLE FILE ENFORCEMENT] ✅ Cleaned up {total_deleted} duplicate file(s), kept earliest only")
        
        return total_deleted
    except Exception as cleanup_err:
        logger.warning(f"[SINGLE FILE ENFORCEMENT] Error during cleanup: {cleanup_err}")
        return 0


def find_earliest_file_in_workspace(
    uploads_dir: str,
    tool_context: Optional[Any] = None,
    workspace_root: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Find the earliest file (by filename timestamp) in the workspace uploads directory.
    
    Args:
        uploads_dir: Path to uploads directory (if None, will try to infer from tool_context)
        tool_context: Tool context with state (optional, used to find uploads_dir if not provided)
        workspace_root: Workspace root directory (optional, used if uploads_dir not found)
        
    Returns:
        Tuple of (earliest_file_path, earliest_filename) or (None, None) if not found
    """
    # Try to get uploads_dir from tool_context if not provided
    if not uploads_dir and tool_context:
        try:
            state = getattr(tool_context, "state", {})
            workspace_paths = state.get("workspace_paths", {})
            uploads_dir = workspace_paths.get("uploads")
        except Exception:
            pass
    
    # Fallback to workspace_root/uploads
    if not uploads_dir and workspace_root:
        uploads_dir = os.path.join(workspace_root, "uploads")
    
    if not uploads_dir or not os.path.exists(uploads_dir):
        return None, None
    
    try:
        import glob
        all_csvs = glob.glob(os.path.join(uploads_dir, "*.csv"))
        # Exclude backup files
        all_csvs = [f for f in all_csvs if not f.endswith(".backup")]
        
        if all_csvs:
            # Sort by filename (earliest timestamp first) to find the original file
            # Files are named like: 1762000000_dataset.csv (timestamp_prefix_name.csv)
            all_csvs.sort(key=lambda p: os.path.basename(p))
            earliest_file = all_csvs[0]
            earliest_filename = os.path.basename(earliest_file)
            logger.info(f"[FILENAME PRESERVATION] Found earliest file: {earliest_filename}")
            return earliest_file, earliest_filename
    except Exception as e:
        logger.warning(f"[FILENAME PRESERVATION] Could not find earliest file: {e}")
    
    return None, None


def preserve_original_filename(
    processed_file_path: str,
    tool_context: Optional[Any] = None,
    uploads_dir: Optional[str] = None,
    workspace_root: Optional[str] = None,
    original_file_path: Optional[str] = None
) -> Tuple[Optional[str], bool]:
    """
    Preserve original filename by:
    1. Backing up the original file (rename to .backup)
    2. Renaming the processed file to the original filename
    3. Updating state to point to the renamed file
    
    This function ensures that after any tool modifies a file:
    - The processed file takes the original filename
    - The original file is backed up (not used)
    - Only one file exists with the original name
    
    Args:
        processed_file_path: Path to the newly created/modified file
        tool_context: Tool context with state (optional)
        uploads_dir: Path to uploads directory (optional, will be inferred)
        workspace_root: Workspace root directory (optional, used if uploads_dir not found)
        original_file_path: Explicit path to original file (optional, will be found if not provided)
        
    Returns:
        Tuple of (final_file_path, backup_created) where:
        - final_file_path: Path to the final renamed file (or processed_file_path if rename failed)
        - backup_created: True if backup was successfully created
    """
    # Find the earliest file if not explicitly provided
    earliest_file = original_file_path
    earliest_filename = None
    
    if not earliest_file:
        earliest_file, earliest_filename = find_earliest_file_in_workspace(
            uploads_dir, tool_context, workspace_root
        )
        if earliest_file:
            earliest_filename = os.path.basename(earliest_file)
    
    if not earliest_file or not earliest_filename:
        logger.warning(f"[FILENAME PRESERVATION] ⚠️ Could not find original file, keeping processed file as-is: {os.path.basename(processed_file_path)}")
        return processed_file_path, False
    
    # Get uploads_dir if not provided
    if not uploads_dir:
        uploads_dir = os.path.dirname(earliest_file)
    
    backup_created = False
    final_file_path = None
    
    try:
        if os.path.exists(earliest_file):
            # Step 1: Backup the original file (rename to .backup)
            backup_path = f"{earliest_file}.backup"
            if os.path.exists(backup_path):
                # If backup already exists, remove it (we want only one backup)
                os.remove(backup_path)
            
            os.rename(earliest_file, backup_path)
            backup_created = True
            logger.info(f"[FILENAME PRESERVATION] ✅ Backed up original file: {os.path.basename(backup_path)}")
            
            # Step 2: Rename processed file to original filename
            final_file_path = os.path.join(uploads_dir, earliest_filename)
            os.rename(processed_file_path, final_file_path)
            logger.info(f"[FILENAME PRESERVATION] ✅ Renamed processed file to original name: {earliest_filename}")
            
            # Step 3: Update state to point to the renamed file
            if tool_context and hasattr(tool_context, "state"):
                try:
                    tool_context.state["default_csv_path"] = final_file_path
                    tool_context.state["dataset_csv_path"] = final_file_path
                    logger.info(f"[FILENAME PRESERVATION] ✅ Updated state.default_csv_path to: {earliest_filename}")
                except Exception as state_err:
                    logger.warning(f"[FILENAME PRESERVATION] Could not update state: {state_err}")
            
        else:
            # Original file doesn't exist, just rename processed file
            final_file_path = os.path.join(uploads_dir, earliest_filename)
            os.rename(processed_file_path, final_file_path)
            logger.info(f"[FILENAME PRESERVATION] ✅ Renamed processed file (no backup needed): {earliest_filename}")
        
        return final_file_path, backup_created
        
    except Exception as rename_err:
        logger.error(f"[FILENAME PRESERVATION] ❌ Failed to rename files: {rename_err}")
        # Fallback: Return processed file path
        return processed_file_path, False

