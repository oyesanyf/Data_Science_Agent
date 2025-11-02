# -*- coding: utf-8 -*-
"""
 Smart File Finder Tool

Discovers available CSV/Parquet files in the workspace with rich metadata.
Helps users find datasets when they're unsure of exact file names/paths.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


def _find_available_csvs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Internal helper to find available CSV files quickly.
    Returns a list of dicts with 'path' and 'filename' keys.
    """
    from .large_data_config import UPLOAD_ROOT
    
    search_dirs = [
        str(UPLOAD_ROOT),
        os.path.join(UPLOAD_ROOT, "uploads") if UPLOAD_ROOT else None,
        ".",
        "data",
        "datasets",
    ]
    
    found_files = []
    
    for base_dir in search_dirs:
        if not base_dir or not os.path.exists(base_dir):
            continue
        
        try:
            for root, dirs, files in os.walk(base_dir):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if file.endswith('.csv'):
                        full_path = os.path.join(root, file)
                        try:
                            # Quick existence check
                            if os.path.exists(full_path):
                                found_files.append({
                                    "path": full_path,
                                    "filename": file,
                                    "directory": root,
                                })
                        except Exception:
                            continue
                
                if len(found_files) >= limit:
                    break
        
        except Exception:
            continue
        
        if len(found_files) >= limit:
            break
    
    # Sort by modification time (newest first)
    found_files.sort(key=lambda x: os.path.getmtime(x["path"]) if os.path.exists(x["path"]) else 0, reverse=True)
    
    return found_files[:limit]


def _suggest_best_match(search_path: str, available_files: List[Dict[str, Any]]) -> Optional[str]:
    """
    Suggest the best matching file from available files based on filename similarity.
    """
    if not available_files:
        return None
    
    search_name = Path(search_path).name.lower()
    
    # Exact match first
    for f in available_files:
        if f["filename"].lower() == search_name:
            return f["path"]
    
    # Partial match
    for f in available_files:
        if search_name in f["filename"].lower() or f["filename"].lower() in search_name:
            return f["path"]
    
    # Return most recent
    return available_files[0]["path"]


def discover_datasets(
    search_pattern: str = "",
    include_stats: str = "yes",
    max_results: int = 20,
) -> Dict[str, Any]:
    """
     DISCOVER AVAILABLE DATASETS
    
    Intelligently searches for CSV/Parquet files in common locations
    and returns detailed metadata to help you choose the right dataset.
    
    Use this when:
    - You uploaded a file but forgot the exact name
    - You want to see all available datasets
    - robust_auto_clean_file() failed to find your file
    - You need to validate file paths before processing
    
    Args:
        search_pattern: Optional filter (e.g., "customer", "sales") - empty string searches all
        include_stats: Calculate row counts and file sizes ("yes"/"no", default "yes")
        max_results: Maximum number of files to return (default: 20)
    
    Returns:
        dict with:
            - status: "success" or "failed"
            - datasets: List of file metadata dicts
            - count: Number of datasets found
            - recommendations: Suggested next actions
    
    Examples:
        >>> # Find all datasets
        >>> discover_datasets()
        
        >>> # Search for customer-related files
        >>> discover_datasets(search_pattern="customer")
        
        >>> # Quick search without stats (faster)
        >>> discover_datasets(include_stats="no", max_results=10)
    """
    # Convert string params to proper types
    search_pattern = search_pattern.strip() if search_pattern else ""
    include_stats_bool = str(include_stats).lower() in ("yes", "true", "1", "y")
    max_results = int(max_results) if max_results else 20
    
    search_dirs = [
        "uploads",
        ".",
        "data",
        "datasets",
        os.path.expanduser("~/Downloads"),
        "cleaned",  # Where robust_auto_clean_file puts cleaned data
    ]
    
    found_files = []
    
    for base_dir in search_dirs:
        if not os.path.exists(base_dir):
            continue
        
        try:
            for root, dirs, files in os.walk(base_dir):
                # Skip hidden and system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
                
                for file in files:
                    if not file.endswith(('.csv', '.parquet', '.tsv', '.txt', '.feather')):
                        continue
                    
                    # Apply search filter
                    if search_pattern and search_pattern.lower() not in file.lower():
                        continue
                    
                    full_path = os.path.join(root, file)
                    
                    try:
                        stat = os.stat(full_path)
                        size_mb = stat.st_size / (1024 * 1024)
                        
                        file_info = {
                            "path": full_path,
                            "filename": file,
                            "directory": root,
                            "size_mb": round(size_mb, 2),
                            "size_bytes": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        }
                        
                        # Optionally calculate row count (can be slow for large files)
                        if include_stats_bool:
                            try:
                                if file.endswith('.parquet'):
                                    try:
                                        import pyarrow.parquet as pq
                                        table = pq.read_table(full_path)
                                        file_info["estimated_rows"] = len(table)
                                        file_info["columns"] = len(table.column_names)
                                    except Exception:
                                        file_info["estimated_rows"] = "Unknown (parquet read error)"
                                        file_info["columns"] = "Unknown"
                                else:
                                    # Quick row count for CSV
                                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        row_count = sum(1 for _ in f)
                                        file_info["estimated_rows"] = max(0, row_count - 1)  # Exclude header
                                        
                                    # Try to get column count from first line
                                    try:
                                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                            first_line = f.readline()
                                            # Try common delimiters
                                            for delim in [',', '\t', ';', '|']:
                                                cols = first_line.split(delim)
                                                if len(cols) > 1:
                                                    file_info["columns"] = len(cols)
                                                    break
                                    except Exception:
                                        file_info["columns"] = "Unknown"
                            except Exception as e:
                                file_info["estimated_rows"] = f"Error: {str(e)[:50]}"
                                file_info["columns"] = "Unknown"
                        else:
                            file_info["estimated_rows"] = "Not calculated (set include_stats='yes')"
                            file_info["columns"] = "Not calculated"
                        
                        found_files.append(file_info)
                        
                        if len(found_files) >= max_results:
                            break
                    except Exception:
                        continue
                
                if len(found_files) >= max_results:
                    break
        except Exception:
            continue
        
        if len(found_files) >= max_results:
            break
    
    # Sort by modification time (most recent first)
    found_files.sort(key=lambda x: x["modified"], reverse=True)
    found_files = found_files[:max_results]
    
    if not found_files:
        return {
            "status": "failed",
            "error": "No datasets found",
            "message": (
                "[X] No CSV/Parquet files found in workspace.\n\n"
                " Next steps:\n"
                "1. Upload a CSV file through the UI\n"
                "2. Place files in: uploads/, data/, or current directory\n"
                "3. Check if files have correct extensions (.csv, .parquet, .tsv)\n"
                f"4. If searching by pattern ('{search_pattern}'), try broader search\n"
            ),
            "datasets": [],
            "count": 0,
            "searched_directories": search_dirs,
            "search_pattern": search_pattern if search_pattern else "(all files)",
        }
    
    # Format recommendations
    recommendations = []
    
    # Recommend most recent file
    if found_files:
        most_recent = found_files[0]
        recommendations.append(
            f" Most recent: robust_auto_clean_file(csv_path='{most_recent['path']}')"
        )
    
    # Recommend largest file (if >1MB)
    largest = max(found_files, key=lambda x: x["size_bytes"])
    if largest["size_mb"] > 1.0 and largest != found_files[0]:
        recommendations.append(
            f" Largest dataset: robust_auto_clean_file(csv_path='{largest['path']}')"
        )
    
    # Create summary
    total_size_mb = sum(f["size_mb"] for f in found_files)
    summary = (
        f"[OK] Found {len(found_files)} dataset(s) (Total: {total_size_mb:.1f} MB)\n"
        f" Searched: {', '.join(search_dirs)}\n"
    )
    if search_pattern:
        summary += f" Filter: '{search_pattern}'\n"
    
    return {
        "status": "success",
        "datasets": found_files,
        "count": len(found_files),
        "total_size_mb": round(total_size_mb, 2),
        "summary": summary,
        "recommendations": recommendations,
        "searched_directories": search_dirs,
        "search_pattern": search_pattern if search_pattern else "(all files)",
        "message": (
            f"{summary}\n"
            f" Next steps:\n"
            f"  1. Pick a dataset from the list above\n"
            f"  2. Clean it: robust_auto_clean_file(csv_path='<path>')\n"
            f"  3. Or preview: preview_metadata_structure(csv_path='<path>')\n"
        ),
    }

