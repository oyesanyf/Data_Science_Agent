"""
Simple fallback tool to copy/save tool results to filesystem files.

This bypasses ADK artifact service complexity and ensures results are ALWAYS
saved to actual files that can be accessed later.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def tool_copy(
    content: str,
    filename: Optional[str] = None,
    workspace_root: Optional[str] = None,
    tool_name: Optional[str] = None,
    format: str = "markdown"
) -> Dict[str, Any]:
    """
    Simple tool to copy/save content to a file in the workspace.
    
    This is a FALLBACK tool that ensures results are ALWAYS saved to filesystem,
    bypassing ADK artifact service complexity.
    
    Args:
        content: The content to save (markdown, JSON, plain text, etc.)
        filename: Optional filename (auto-generated if not provided)
        workspace_root: Path to workspace root (required)
        tool_name: Name of the tool that generated this content (for filename)
        format: Output format ("markdown", "json", "txt")
    
    Returns:
        Dict with:
            - status: "success" or "error"
            - file_path: Full path to saved file
            - filename: Just the filename
            - size_bytes: Size of file written
            - message: Human-readable message
    """
    try:
        # Validate inputs
        if not content:
            return {
                "status": "error",
                "message": "No content provided to save",
                "file_path": None
            }
        
        if not workspace_root:
            return {
                "status": "error",
                "message": "No workspace_root provided - cannot determine where to save file",
                "file_path": None
            }
        
        # Determine output folder based on format
        format_to_folder = {
            "markdown": "reports",
            "md": "reports",
            "json": "results",
            "txt": "reports",
            "log": "logs"
        }
        folder = format_to_folder.get(format.lower(), "reports")
        
        # Create output directory
        ws_root = Path(workspace_root)
        output_dir = ws_root / folder
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            safe_tool_name = (tool_name or "tool_output").replace(" ", "_")
            ext = "md" if format in ["markdown", "md"] else format
            filename = f"{timestamp}_{safe_tool_name}.{ext}"
        
        # Ensure filename has correct extension
        if not filename.endswith(f".{format}"):
            if "." not in filename:
                filename = f"{filename}.{format}"
        
        # Write file
        file_path = output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        size_bytes = file_path.stat().st_size
        
        logger.info(f"[TOOL_COPY] ✅ Saved {size_bytes} bytes to: {file_path}")
        
        return {
            "status": "success",
            "file_path": str(file_path),
            "filename": filename,
            "folder": folder,
            "size_bytes": size_bytes,
            "message": f"✅ Saved {format.upper()} file: {filename} ({size_bytes:,} bytes)",
            "__display__": f"✅ **File Saved Successfully**\n\n"
                          f"- **Location**: `{file_path}`\n"
                          f"- **Folder**: `{folder}/`\n"
                          f"- **Filename**: `{filename}`\n"
                          f"- **Size**: {size_bytes:,} bytes\n"
                          f"- **Format**: {format.upper()}\n"
        }
        
    except Exception as e:
        logger.error(f"[TOOL_COPY] ❌ Failed to save file: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ Failed to save file: {str(e)}",
            "file_path": None,
            "error": str(e)
        }


def auto_save_tool_result(
    result: Dict[str, Any],
    workspace_root: str,
    tool_name: str,
    save_markdown: bool = True,
    save_json: bool = True
) -> Dict[str, Any]:
    """
    Automatically save tool results to filesystem files.
    
    This is called automatically as a fallback to ensure results are always saved,
    even if ADK artifact service fails.
    
    Args:
        result: The tool's result dictionary
        workspace_root: Path to workspace root
        tool_name: Name of the tool
        save_markdown: Whether to save human-readable markdown
        save_json: Whether to save machine-readable JSON
    
    Returns:
        Dict with saved file paths and status
    """
    saved_files = []
    errors = []
    
    try:
        # Extract displayable content for markdown
        display_content = (
            result.get("__display__") or 
            result.get("message") or 
            result.get("output") or
            str(result)
        )
        
        # Save markdown (human-readable)
        if save_markdown and display_content:
            md_result = tool_copy(
                content=display_content,
                workspace_root=workspace_root,
                tool_name=tool_name,
                format="markdown"
            )
            if md_result.get("status") == "success":
                saved_files.append(md_result["file_path"])
            else:
                errors.append(f"Markdown save failed: {md_result.get('message')}")
        
        # Save JSON (machine-readable)
        if save_json:
            import json
            json_content = json.dumps(result, indent=2, default=str)
            json_result = tool_copy(
                content=json_content,
                workspace_root=workspace_root,
                tool_name=tool_name,
                format="json"
            )
            if json_result.get("status") == "success":
                saved_files.append(json_result["file_path"])
            else:
                errors.append(f"JSON save failed: {json_result.get('message')}")
        
        return {
            "status": "success" if saved_files else "error",
            "saved_files": saved_files,
            "saved_count": len(saved_files),
            "errors": errors,
            "message": f"✅ Saved {len(saved_files)} file(s)" if saved_files else "❌ No files saved"
        }
        
    except Exception as e:
        logger.error(f"[AUTO_SAVE] Failed to auto-save tool result: {e}", exc_info=True)
        return {
            "status": "error",
            "saved_files": saved_files,
            "saved_count": len(saved_files),
            "errors": errors + [str(e)],
            "message": f"❌ Auto-save failed: {str(e)}"
        }

