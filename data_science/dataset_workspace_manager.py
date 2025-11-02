# -*- coding: utf-8 -*-
"""
Dataset Workspace Manager - LLM-Guided Directory Structure & File Organization

This module provides intelligent workspace creation and file organization
based on dataset names, allowing the LLM to create structured directories
and automatically save files in appropriate locations.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# [CRITICAL FIX] Standard subdirectories - MUST MATCH artifact_manager.py structure!
# Tools expect these exact folder names: uploads, data, models, reports, results, plots, metrics, indexes, logs, tmp, manifests, unstructured
STANDARD_SUBDIRS = {
    "uploads": {
        "description": "Original uploaded files",
        "extensions": [".csv", ".xlsx", ".tsv", ".json", ".txt"],
    },
    "data": {
        "description": "Processed and cleaned datasets",
        "extensions": [".csv", ".parquet", ".feather", ".xlsx", ".tsv"],
    },
    "models": {
        "description": "Trained machine learning models",
        "extensions": [".pkl", ".joblib", ".onnx", ".pb", ".h5", ".pt", ".pth"],
    },
    "reports": {
        "description": "Analysis reports and markdown documentation",
        "extensions": [".md", ".pdf", ".html", ".docx", ".txt"],
    },
    "results": {
        "description": "JSON results from tool executions",
        "extensions": [".json", ".yaml", ".yml"],
    },
    "plots": {
        "description": "Data visualizations and charts",
        "extensions": [".png", ".jpg", ".jpeg", ".svg", ".pdf", ".html", ".gif", ".webp"],
    },
    "metrics": {
        "description": "Evaluation metrics and statistics",
        "extensions": [".json", ".csv", ".yaml", ".yml"],
    },
    "indexes": {
        "description": "Search indexes and vector stores",
        "extensions": [".pkl", ".faiss", ".index", ".npy", ".npz"],
    },
    "logs": {
        "description": "Execution logs and debugging information",
        "extensions": [".log", ".txt"],
    },
    "tmp": {
        "description": "Temporary working files",
        "extensions": ["*"],
    },
    "manifests": {
        "description": "Workspace manifests and metadata",
        "extensions": [".json", ".yaml"],
    },
    "unstructured": {
        "description": "Unstructured data (images, PDFs, documents)",
        "extensions": [".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg"],
    },
}


def _sanitize_dataset_name(name: str) -> str:
    """
    Sanitize dataset name to be filesystem-safe.
    
    Args:
        name: Original dataset name
        
    Returns:
        Sanitized name safe for filesystem use
    """
    if not name:
        return "unnamed_dataset"
    
    # Remove or replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '_', name.strip())
    # Replace multiple underscores/spaces with single underscore
    name = re.sub(r'[\s_]+', '_', name)
    # Remove leading/trailing underscores and dots
    name = name.strip('._')
    # Limit length
    name = name[:100] if len(name) > 100 else name
    # Ensure it's not empty
    if not name:
        name = "unnamed_dataset"
    
    return name.lower()


def _llm_suggest_dataset_name(headers: List[str] = None, 
                               sample_data: str = "",
                               file_path: str = None,
                               context: str = "") -> Optional[str]:
    """
    Use LLM to suggest an intelligent dataset name based on data characteristics.
    
    Args:
        headers: Column headers from the dataset
        sample_data: Sample row of data (for context)
        file_path: Original file path
        context: Additional context about the dataset
        
    Returns:
        Suggested dataset name or None if LLM unavailable
    """
    enable_llm = os.getenv("ENABLE_LLM_DATASET_NAMING", "1").lower() in ("1", "true", "yes")
    if not enable_llm:
        return None
    
    try:
        model = os.getenv("LLM_DATASET_NAMING_MODEL", "gpt-4o-mini")
        
        # Build context for LLM
        headers_str = ", ".join(headers[:10]) if headers else "Unknown"
        sample_str = sample_data[:200] if sample_data else ""
        
        prompt = (
            "You are helping organize data science files. Suggest a short, descriptive, "
            "filesystem-safe dataset name (lowercase, underscores, <= 50 chars, no spaces).\n\n"
            f"Column headers: {headers_str}\n"
            f"File path: {file_path or 'Unknown'}\n"
            f"Sample data: {sample_str}\n"
            f"Context: {context}\n\n"
            "Return ONLY the dataset name, nothing else. Make it descriptive but concise.\n"
            "Dataset name:"
        )
        
        # Try litellm first
        try:
            from litellm import completion
            response = completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50
            )
            suggested_name = response.choices[0].message.content.strip()
        except Exception:
            # Fallback to OpenAI SDK
            try:
                from openai import OpenAI
                client = OpenAI()
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50
                )
                suggested_name = response.choices[0].message.content.strip()
            except Exception:
                return None
        
        # Sanitize the LLM suggestion
        suggested_name = _sanitize_dataset_name(suggested_name)
        
        # Ensure it's not too generic
        generic_names = ["data", "dataset", "file", "upload", "csv"]
        if suggested_name.lower() in generic_names:
            return None
        
        return suggested_name if len(suggested_name) >= 3 else None
        
    except Exception as e:
        logger.debug(f"LLM dataset naming failed: {e}")
        return None


def derive_dataset_name(file_path: str = None,
                        headers: List[str] = None,
                        sample_data: str = "",
                        context: str = "",
                        use_llm: bool = True) -> str:
    """
    Intelligently derive a dataset name from available information.
    
    Priority order:
    1. LLM suggestion (if enabled and headers provided)
    2. File basename (sanitized)
    3. Headers-based name
    4. Fallback to "dataset"
    
    Args:
        file_path: Path to the dataset file
        headers: Column headers from dataset
        sample_data: Sample data row for context
        context: Additional context
        use_llm: Whether to use LLM for naming
        
    Returns:
        Derived dataset name
    """
    # Try LLM naming first
    if use_llm and headers:
        llm_name = _llm_suggest_dataset_name(
            headers=headers,
            sample_data=sample_data,
            file_path=file_path,
            context=context
        )
        if llm_name:
            logger.info(f"LLM suggested dataset name: {llm_name}")
            return llm_name
    
    # Fallback to file-based naming
    if file_path:
        base_name = Path(file_path).stem
        # Remove timestamp prefixes
        base_name = re.sub(r'^(uploaded_)?\d{10,}_?', '', base_name)
        base_name = re.sub(r'^\d{4}-\d{2}-\d{2}_', '', base_name)
        sanitized = _sanitize_dataset_name(base_name)
        if sanitized and sanitized != "unnamed_dataset":
            return sanitized
    
    # Headers-based naming
    if headers:
        # Combine first few headers
        header_name = "_".join(_sanitize_dataset_name(h) for h in headers[:3])
        header_name = header_name[:50]
        if header_name and len(header_name) >= 3:
            return header_name
    
    return "dataset"


def create_workspace_structure(dataset_name: str,
                                base_root: str = None,
                                subdirs: Dict[str, Dict] = None) -> Tuple[Path, Dict[str, str]]:
    """
    Create a comprehensive, timestamped workspace directory structure for a dataset.
    
    Structure created:
        {base_root}/{dataset_name}/{timestamp}/
          ├─ data/
          ├─ models/
          ...
          └─ manifest.json
    
    Args:
        dataset_name: Name of the dataset (will be sanitized)
        base_root: Base root directory (default from large_data_config.WORKSPACES_ROOT)
        subdirs: Custom subdirectories to create (optional)
        
    Returns:
        Tuple of (workspace_path, subdirectory_paths_dict)
    """
    # Determine base root from centralized config
    if not base_root:
        try:
            from .large_data_config import WORKSPACES_ROOT
            base_root = str(WORKSPACES_ROOT)
        except ImportError:
            logger.warning("Could not import WORKSPACES_ROOT, using fallback.")
            # Fallback path consistent with large_data_config.py
            base_root = str(Path("data_science") / ".uploaded" / ".uploaded_workspaces")

    # Sanitize dataset name
    safe_name = _sanitize_dataset_name(dataset_name)
    
    # Generate a timestamp for the new workspace subdirectory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create workspace root: {base_root}/{safe_name}/{timestamp}
    workspace_root = Path(base_root) / safe_name / timestamp
    workspace_root.mkdir(parents=True, exist_ok=True)
    
    # Use provided subdirs or standard ones
    subdirs_to_create = subdirs if subdirs else STANDARD_SUBDIRS
    
    # Create all subdirectories
    subdirectory_paths = {}
    for subdir_name, subdir_info in subdirs_to_create.items():
        subdir_path = workspace_root / subdir_name
        subdir_path.mkdir(parents=True, exist_ok=True)
        subdirectory_paths[subdir_name] = str(subdir_path)
    
    # Create manifest file with metadata
    manifest = {
        "dataset_name": dataset_name,
        "safe_name": safe_name,
        "timestamp": timestamp,
        "created_at": datetime.now().isoformat(),
        "workspace_root": str(workspace_root),
        "subdirectories": subdirectory_paths,
        "structure_version": "1.1"  # Incremented version
    }
    
    manifest_path = workspace_root / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"Created timestamped workspace structure: {workspace_root}")
    logger.info(f"Subdirectories: {', '.join(subdirs_to_create.keys())}")
    
    return workspace_root, subdirectory_paths


def get_file_destination(file_path: str,
                         workspace_paths: Dict[str, str],
                         file_type: str = None) -> str:
    """
    Determine the appropriate subdirectory for a file based on its extension or type.
    
    Args:
        file_path: Path or filename to categorize
        workspace_paths: Dictionary of workspace subdirectory paths
        file_type: Explicit file type override (e.g., "model", "plot", "data")
        
    Returns:
        Full path to destination directory
    """
    # If explicit type provided, use it
    if file_type and file_type in workspace_paths:
        return workspace_paths[file_type]
    
    # Determine from file extension
    file_ext = Path(file_path).suffix.lower()
    
    # Map extensions to subdirectories
    for subdir_name, subdir_info in STANDARD_SUBDIRS.items():
        if file_ext in subdir_info.get("extensions", []):
            if subdir_name in workspace_paths:
                return workspace_paths[subdir_name]
    
    # Default to data directory for unknown types
    return workspace_paths.get("data", list(workspace_paths.values())[0] if workspace_paths else ".")


def save_to_workspace(file_path: str,
                      destination_name: str = None,
                      workspace_paths: Dict[str, str] = None,
                      file_type: str = None,
                      dataset_name: str = None,
                      copy: bool = True) -> str:
    """
    Save a file to the appropriate location in the workspace structure.
    
    This function intelligently determines where to save the file based on:
    - File extension
    - Explicit file_type parameter
    - Workspace structure
    
    Args:
        file_path: Source file path to save
        destination_name: Optional custom filename for destination
        workspace_paths: Workspace subdirectory paths (auto-created if not provided)
        file_type: Explicit file type ("data", "model", "plot", etc.)
        dataset_name: Dataset name (for auto-creating workspace if needed)
        copy: If True, copy file; if False, move file
        
    Returns:
        Full path to saved file
    """
    source_path = Path(file_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")
    
    # Ensure workspace exists
    if not workspace_paths:
        if dataset_name:
            _, workspace_paths = create_workspace_structure(dataset_name)
        else:
            raise ValueError("Either workspace_paths or dataset_name must be provided")
    
    # Determine destination directory
    dest_dir = get_file_destination(
        file_path,
        workspace_paths,
        file_type=file_type
    )
    
    # Determine destination filename
    if destination_name:
        dest_filename = destination_name
    else:
        dest_filename = source_path.name
    
    dest_path = Path(dest_dir) / dest_filename
    
    # Copy or move file
    if copy:
        import shutil
        shutil.copy2(source_path, dest_path)
        logger.info(f"Copied {source_path} -> {dest_path}")
    else:
        import shutil
        shutil.move(source_path, dest_path)
        logger.info(f"Moved {source_path} -> {dest_path}")
    
    return str(dest_path)


def load_workspace_info(dataset_name: str, base_root: str = None) -> Dict[str, Any]:
    """
    Load workspace information from the most recent timestamped manifest.
    
    Args:
        dataset_name: Name of the dataset
        base_root: Base root directory
        
    Returns:
        Workspace manifest information from the latest workspace, or {} if none found.
    """
    # Determine base root from centralized config
    if not base_root:
        try:
            from .large_data_config import WORKSPACES_ROOT
            base_root = str(WORKSPACES_ROOT)
        except ImportError:
            logger.warning("Could not import WORKSPACES_ROOT, using fallback.")
            base_root = str(Path("data_science") / ".uploaded" / ".uploaded_workspaces")

    safe_name = _sanitize_dataset_name(dataset_name)
    dataset_root = Path(base_root) / safe_name

    if not dataset_root.is_dir():
        return {}

    # Find the most recent timestamped subdirectory
    latest_workspace_dir = None
    latest_timestamp = ""

    for subdir in dataset_root.iterdir():
        # Check if it's a directory and its name matches the timestamp format
        if subdir.is_dir() and re.match(r"\d{8}_\d{6}", subdir.name):
            if subdir.name > latest_timestamp:
                latest_timestamp = subdir.name
                latest_workspace_dir = subdir

    if not latest_workspace_dir:
        # Check for legacy, non-timestamped workspace with a manifest
        legacy_manifest_path = dataset_root / "manifest.json"
        if legacy_manifest_path.exists():
            logger.info(f"Found legacy workspace manifest: {legacy_manifest_path}")
            with open(legacy_manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    manifest_path = latest_workspace_dir / "manifest.json"
    
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {}


def list_workspace_files(dataset_name: str,
                        file_type: str = None,
                        base_root: str = None) -> List[Dict[str, Any]]:
    """
    List all files in a workspace, optionally filtered by type.
    
    Args:
        dataset_name: Name of the dataset
        file_type: Optional filter by file type (subdirectory name)
        base_root: Base root directory
        
    Returns:
        List of file information dictionaries
    """
    workspace_info = load_workspace_info(dataset_name, base_root)
    
    if not workspace_info:
        return []
    
    workspace_root = Path(workspace_info.get("workspace_root"))
    subdirectories = workspace_info.get("subdirectories", {})
    
    files_list = []
    
    # If specific type requested, only scan that directory
    if file_type and file_type in subdirectories:
        dir_to_scan = Path(subdirectories[file_type])
        if dir_to_scan.exists():
            for file_path in dir_to_scan.rglob("*"):
                if file_path.is_file():
                    files_list.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "type": file_type,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })
    else:
        # Scan all subdirectories
        for subdir_name, subdir_path in subdirectories.items():
            subdir = Path(subdir_path)
            if subdir.exists():
                for file_path in subdir.rglob("*"):
                    if file_path.is_file():
                        files_list.append({
                            "name": file_path.name,
                            "path": str(file_path),
                            "type": subdir_name,
                            "size": file_path.stat().st_size,
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        })
    
    return sorted(files_list, key=lambda x: x["modified"], reverse=True)


# Convenience function for LLM to use
def ensure_dataset_workspace(dataset_name: str = None,
                            file_path: str = None,
                            headers: List[str] = None,
                            sample_data: str = "",
                            context: str = "") -> Tuple[str, Dict[str, str]]:
    """
    Ensure workspace exists for a dataset, creating it if necessary.
    
    This is the main entry point for LLMs to use when setting up workspace structures.
    
    Args:
        dataset_name: Explicit dataset name (optional)
        file_path: Path to dataset file (used for naming if dataset_name not provided)
        headers: Column headers (used for LLM naming)
        sample_data: Sample data (used for LLM naming)
        context: Additional context (used for LLM naming)
        
    Returns:
        Tuple of (workspace_root_path, subdirectory_paths_dict)
    """
    # Derive dataset name if not provided
    if not dataset_name:
        dataset_name = derive_dataset_name(
            file_path=file_path,
            headers=headers,
            sample_data=sample_data,
            context=context
        )
    
    # Check if workspace already exists
    workspace_info = load_workspace_info(dataset_name)
    
    if workspace_info and workspace_info.get("subdirectories"):
        # Workspace exists, return existing paths
        workspace_root = workspace_info["workspace_root"]
        subdirectory_paths = workspace_info["subdirectories"]
        logger.info(f"Using existing workspace: {workspace_root}")
        return workspace_root, subdirectory_paths
    
    # Create new workspace
    workspace_root, subdirectory_paths = create_workspace_structure(dataset_name)
    return str(workspace_root), subdirectory_paths

