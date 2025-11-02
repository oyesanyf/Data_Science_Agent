# -*- coding: utf-8 -*-
"""
Workspace Tools - ADK-safe wrappers for LLM-guided workspace management
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def create_dataset_workspace_tool(
    dataset_name: str = "",
    file_path: str = "",
    headers: str = "",
    context: str = "",
    **kwargs
) -> Dict[str, Any]:
    """
    Create or ensure a workspace directory structure exists for a dataset.
    
    This tool allows the LLM to intelligently organize files by dataset name,
    creating structured directories for different file types (data, models, plots, etc.).
    
    Args:
        dataset_name: Name for the dataset workspace (optional, auto-derived if not provided)
        file_path: Path to dataset file (used for naming and organization)
        headers: Comma-separated column headers (used for LLM naming)
        context: Additional context about the dataset
        
    Returns:
        Dictionary with workspace information and paths
        
    Examples:
        - create_dataset_workspace_tool(file_path="customer_data.csv")
        - create_dataset_workspace_tool(dataset_name="sales_analysis", headers="date,sales,region")
    """
    from .dataset_workspace_manager import (
        ensure_dataset_workspace,
        derive_dataset_name,
        create_workspace_structure
    )
    
    try:
        # Parse headers if provided as string
        headers_list = None
        if headers:
            headers_list = [h.strip() for h in headers.split(",") if h.strip()]
        
        # Create or get workspace
        workspace_root, subdirectory_paths = ensure_dataset_workspace(
            dataset_name=dataset_name if dataset_name else None,
            file_path=file_path if file_path else None,
            headers=headers_list,
            context=context
        )
        
        result = {
            "status": "success",
            "workspace_root": workspace_root,
            "subdirectories": subdirectory_paths,
            "message": (
                f"✅ Workspace created/verified for dataset: {Path(workspace_root).name}\n"
                f"📁 Workspace root: {workspace_root}\n"
                f"📂 Subdirectories available: {', '.join(subdirectory_paths.keys())}"
            )
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "message": f"Failed to create workspace: {e}"
        }


def save_file_to_workspace_tool(
    file_path: str,
    dataset_name: str = "",
    destination_name: str = "",
    file_type: str = "",
    **kwargs
) -> Dict[str, Any]:
    """
    Save a file to the appropriate location in a dataset workspace.
    
    Automatically determines the correct subdirectory based on file extension
    (e.g., .pkl → models/, .png → plots/, .csv → data/).
    
    Args:
        file_path: Source file path to save
        dataset_name: Dataset name (workspace will be created if needed)
        destination_name: Optional custom filename for destination
        file_type: Explicit file type override ("data", "model", "plot", "report", etc.)
        
    Returns:
        Dictionary with saved file information
        
    Examples:
        - save_file_to_workspace_tool(file_path="model.pkl", dataset_name="customer_analysis", file_type="model")
        - save_file_to_workspace_tool(file_path="plot.png", dataset_name="sales_data")
    """
    from pathlib import Path
    from .dataset_workspace_manager import (
        save_to_workspace,
        ensure_dataset_workspace
    )
    
    try:
        source_path = Path(file_path)
        if not source_path.exists():
            return {
                "status": "failed",
                "error": f"Source file not found: {file_path}",
                "message": f"Source file not found: {file_path}"
            }
        
        # Ensure workspace exists
        if not dataset_name:
            # Try to derive from file path or use default
            dataset_name = source_path.stem or "dataset"
        
        _, workspace_paths = ensure_dataset_workspace(dataset_name=dataset_name)
        
        # Save file to workspace
        saved_path = save_to_workspace(
            file_path=str(source_path),
            destination_name=destination_name if destination_name else None,
            workspace_paths=workspace_paths,
            file_type=file_type if file_type else None,
            dataset_name=dataset_name,
            copy=True
        )
        
        return {
            "status": "success",
            "saved_path": saved_path,
            "file_type": Path(saved_path).parent.name,
            "message": (
                f"✅ File saved to workspace\n"
                f"📁 Destination: {saved_path}\n"
                f"📂 Category: {Path(saved_path).parent.name}"
            )
        }
        
    except Exception as e:
        logger.error(f"Failed to save file to workspace: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "message": f"Failed to save file: {e}"
        }


def list_workspace_files_tool(
    dataset_name: str,
    file_type: str = "",
    **kwargs
) -> Dict[str, Any]:
    """
    List all files in a dataset workspace, optionally filtered by type.
    
    Args:
        dataset_name: Name of the dataset workspace
        file_type: Optional filter by file type ("data", "model", "plot", etc.)
        
    Returns:
        Dictionary with list of files and their metadata
        
    Examples:
        - list_workspace_files_tool(dataset_name="customer_analysis")
        - list_workspace_files_tool(dataset_name="sales_data", file_type="plots")
    """
    from .dataset_workspace_manager import list_workspace_files
    
    try:
        files = list_workspace_files(
            dataset_name=dataset_name,
            file_type=file_type if file_type else None
        )
        
        if not files:
            return {
                "status": "success",
                "files": [],
                "count": 0,
                "message": f"No files found in workspace: {dataset_name}"
            }
        
        # Group by type
        files_by_type = {}
        for file_info in files:
            file_type_key = file_info["type"]
            if file_type_key not in files_by_type:
                files_by_type[file_type_key] = []
            files_by_type[file_type_key].append(file_info)
        
        message_lines = [
            f"✅ Found {len(files)} file(s) in workspace: {dataset_name}",
            ""
        ]
        
        for ftype, type_files in files_by_type.items():
            message_lines.append(f"📂 {ftype}: {len(type_files)} file(s)")
            for f in type_files[:5]:  # Show first 5 per type
                message_lines.append(f"   • {f['name']}")
            if len(type_files) > 5:
                message_lines.append(f"   ... and {len(type_files) - 5} more")
        
        return {
            "status": "success",
            "files": files,
            "count": len(files),
            "files_by_type": files_by_type,
            "message": "\n".join(message_lines)
        }
        
    except Exception as e:
        logger.error(f"Failed to list workspace files: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "message": f"Failed to list files: {e}"
        }


def get_workspace_info_tool(
    dataset_name: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Get information about a dataset workspace.
    
    Args:
        dataset_name: Name of the dataset workspace
        
    Returns:
        Dictionary with workspace information
        
    Examples:
        - get_workspace_info_tool(dataset_name="customer_analysis")
    """
    from .dataset_workspace_manager import load_workspace_info
    from pathlib import Path
    
    try:
        info = load_workspace_info(dataset_name)
        
        if not info:
            return {
                "status": "failed",
                "error": f"Workspace not found: {dataset_name}",
                "message": f"Workspace not found: {dataset_name}"
            }
        
        workspace_root = Path(info.get("workspace_root", ""))
        subdirectories = info.get("subdirectories", {})
        
        message_lines = [
            f"📊 Workspace Information: {dataset_name}",
            f"📁 Root: {workspace_root}",
            f"📅 Created: {info.get('created_at', 'Unknown')}",
            "",
            "📂 Subdirectories:"
        ]
        
        for subdir_name, subdir_path in subdirectories.items():
            subdir = Path(subdir_path)
            file_count = len(list(subdir.rglob("*"))) if subdir.exists() else 0
            message_lines.append(f"   • {subdir_name}: {file_count} file(s) - {subdir_path}")
        
        return {
            "status": "success",
            "workspace_info": info,
            "workspace_root": str(workspace_root),
            "subdirectories": subdirectories,
            "message": "\n".join(message_lines)
        }
        
    except Exception as e:
        logger.error(f"Failed to get workspace info: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "message": f"Failed to get workspace info: {e}"
        }

