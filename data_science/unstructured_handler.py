"""
Unstructured data handler for processing various file types.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from .artifact_utils import sync_push_artifact, _exists, guess_mime

logger = logging.getLogger(__name__)

def process_unstructured_file(
    file_path: str, 
    tool_context=None, 
    **kwargs
) -> Dict[str, Any]:
    """
    Process unstructured data files (PDFs, images, documents, etc.)
    and save them to the unstructured workspace folder.
    """
    if not _exists(file_path):
        return {
            "status": "failed",
            "message": f"File not found: {file_path}"
        }
    
    file_path = Path(file_path)
    state = getattr(tool_context, "state", {}) if tool_context else {}
    workspace_paths = state.get("workspace_paths", {})
    unstructured_dir = workspace_paths.get("unstructured")
    
    if not unstructured_dir:
        return {
            "status": "failed", 
            "message": "Unstructured workspace not initialized"
        }
    
    # Ensure unstructured directory exists
    Path(unstructured_dir).mkdir(parents=True, exist_ok=True)
    
    # Copy file to unstructured directory
    try:
        dest_path = Path(unstructured_dir) / file_path.name
        import shutil
        shutil.copy2(file_path, dest_path)
        
        # Register artifact
        from .artifact_manager import register_artifact
        register_artifact(state, str(dest_path), kind="unstructured", label=file_path.stem)
        
        # Push to UI artifacts
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                sync_push_artifact(tool_context, str(dest_path), display_name=file_path.name)
            except Exception as e:
                logger.warning(f"Failed to push unstructured file to UI: {e}")
        
        return {
            "status": "success",
            "message": f" Unstructured file processed: **{file_path.name}** (see Artifacts)",
            "ui_text": f" Unstructured file processed: **{file_path.name}** (see Artifacts)",
            "file_path": str(dest_path),
            "file_type": file_path.suffix.lower(),
            "mime_type": guess_mime(str(dest_path)),
            "artifacts": [{
                "path": str(dest_path),
                "kind": "unstructured", 
                "label": file_path.stem,
                "mime": guess_mime(str(dest_path))
            }]
        }
        
    except Exception as e:
        logger.error(f"Failed to process unstructured file: {e}")
        return {
            "status": "failed",
            "message": f"Failed to process unstructured file: {str(e)}"
        }

def list_unstructured_files(tool_context=None, **kwargs) -> Dict[str, Any]:
    """
    List all unstructured files in the workspace.
    """
    state = getattr(tool_context, "state", {}) if tool_context else {}
    workspace_paths = state.get("workspace_paths", {})
    unstructured_dir = workspace_paths.get("unstructured")
    
    if not unstructured_dir or not Path(unstructured_dir).exists():
        return {
            "status": "success",
            "message": "No unstructured files found",
            "files": []
        }
    
    try:
        files = []
        for file_path in Path(unstructured_dir).iterdir():
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime,
                    "mime_type": guess_mime(str(file_path))
                })
        
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "status": "success",
            "message": f" Found {len(files)} unstructured files",
            "ui_text": f" Found {len(files)} unstructured files",
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        logger.error(f"Failed to list unstructured files: {e}")
        return {
            "status": "failed",
            "message": f"Failed to list unstructured files: {str(e)}"
        }

def analyze_unstructured_content(
    file_path: str,
    tool_context=None,
    **kwargs
) -> Dict[str, Any]:
    """
    Analyze unstructured content and extract insights.
    """
    if not _exists(file_path):
        return {
            "status": "failed",
            "message": f"File not found: {file_path}"
        }
    
    file_path = Path(file_path)
    file_type = file_path.suffix.lower()
    
    try:
        if file_type == '.pdf':
            return _analyze_pdf(file_path, tool_context)
        elif file_type in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return _analyze_image(file_path, tool_context)
        elif file_type in ['.txt', '.md', '.csv']:
            return _analyze_text(file_path, tool_context)
        else:
            return {
                "status": "success",
                "message": f" File type {file_type} detected but analysis not implemented yet",
                "file_type": file_type,
                "file_name": file_path.name
            }
    except Exception as e:
        logger.error(f"Failed to analyze unstructured content: {e}")
        return {
            "status": "failed",
            "message": f"Failed to analyze content: {str(e)}"
        }

def _analyze_pdf(file_path: Path, tool_context) -> Dict[str, Any]:
    """Analyze PDF content."""
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            # Extract text from first few pages
            text_content = ""
            for i in range(min(3, num_pages)):
                page = pdf_reader.pages[i]
                text_content += page.extract_text() + "\n"
            
            return {
                "status": "success",
                "message": f" PDF analyzed: {num_pages} pages, {len(text_content)} characters extracted",
                "ui_text": f" PDF analyzed: {num_pages} pages, {len(text_content)} characters extracted",
                "file_type": "pdf",
                "num_pages": num_pages,
                "text_preview": text_content[:500] + "..." if len(text_content) > 500 else text_content,
                "full_text_length": len(text_content)
            }
    except ImportError:
        return {
            "status": "success",
            "message": f" PDF file detected but PyPDF2 not available for analysis",
            "file_type": "pdf",
            "file_name": file_path.name
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Failed to analyze PDF: {str(e)}"
        }

def _analyze_image(file_path: Path, tool_context) -> Dict[str, Any]:
    """Analyze image content."""
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            width, height = img.size
            mode = img.mode
            format_name = img.format
            
            return {
                "status": "success",
                "message": f" Image analyzed: {width}x{height}, {mode} mode, {format_name} format",
                "ui_text": f" Image analyzed: {width}x{height}, {mode} mode, {format_name} format",
                "file_type": "image",
                "dimensions": f"{width}x{height}",
                "mode": mode,
                "format": format_name
            }
    except ImportError:
        return {
            "status": "success",
            "message": f" Image file detected but PIL not available for analysis",
            "file_type": "image",
            "file_name": file_path.name
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Failed to analyze image: {str(e)}"
        }

def _analyze_text(file_path: Path, tool_context) -> Dict[str, Any]:
    """Analyze text content."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
            lines = content.split('\n')
            words = content.split()
            
            return {
                "status": "success",
                "message": f" Text analyzed: {len(lines)} lines, {len(words)} words, {len(content)} characters",
                "ui_text": f" Text analyzed: {len(lines)} lines, {len(words)} words, {len(content)} characters",
                "file_type": "text",
                "lines": len(lines),
                "words": len(words),
                "characters": len(content),
                "preview": content[:300] + "..." if len(content) > 300 else content
            }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Failed to analyze text: {str(e)}"
        }
