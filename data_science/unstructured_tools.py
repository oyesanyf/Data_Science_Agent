"""
ADK-safe wrappers for unstructured data tools.
"""
from typing import Dict, Any
from .unstructured_handler import process_unstructured_file, list_unstructured_files, analyze_unstructured_content
from .ds_tools import ensure_display_fields

@ensure_display_fields
def process_unstructured_tool(file_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for processing unstructured files."""
    return process_unstructured_file(file_path=file_path, **kwargs)

@ensure_display_fields
def list_unstructured_tool(**kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for listing unstructured files."""
    return list_unstructured_files(**kwargs)

@ensure_display_fields
def analyze_unstructured_tool(file_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for analyzing unstructured content."""
    return analyze_unstructured_content(file_path=file_path, **kwargs)