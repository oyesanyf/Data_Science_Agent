# -*- coding: utf-8 -*-
"""
Universal Artifact Creation for All Tools

This module ensures that ALL tool outputs are automatically saved as artifacts
using ADK's artifact service pattern, making them accessible via:
- {artifact.filename} placeholders in prompts
- LoadArtifactsTool for LLM awareness
- tool_context.save_artifact() for persistence

Based on ADK documentation patterns:
- Artifacts are saved as google.genai.types.Part objects
- Can be text, binary (images, PDFs), or structured data (JSON)
- Automatically versioned and accessible across sessions
"""

import os
import json
import logging
import mimetypes
import asyncio
import inspect
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

try:
    from google.genai import types
except ImportError:
    types = None

logger = logging.getLogger(__name__)

# Tools logger for artifact operations
try:
    from .logging_config import get_tools_logger
    tools_logger = get_tools_logger()
except ImportError:
    tools_logger = logger  # Fallback to default logger


def ensure_artifact_creation(result: Dict[str, Any], tool_name: str, tool_context: Any) -> Dict[str, Any]:
    """
    Universal artifact creator - ensures ALL tool outputs are saved as artifacts.
    
    This function:
    1. Detects files/paths in tool results
    2. Saves them via ADK artifact service
    3. Adds artifact metadata to result
    4. Creates JSON summaries for LLM accessibility
    
    Args:
        result: Tool result dictionary
        tool_name: Name of the tool (for artifact naming)
        tool_context: ADK ToolContext with save_artifact method
        
    Returns:
        Updated result with artifact information
    """
    if not isinstance(result, dict):
        return result
    
    if not tool_context or not hasattr(tool_context, 'save_artifact'):
        logger.debug(f"[ARTIFACT] No tool_context.save_artifact available for {tool_name}")
        return result
    
    artifacts_created = []
    
    # 1. Extract file paths from common result keys
    file_paths = _extract_file_paths(result)
    
    # 2. Save each file as artifact
    tools_logger.info(f"[ARTIFACT] Processing {len(file_paths)} file(s) for tool '{tool_name}'")
    for file_path, artifact_type in file_paths:
        if os.path.exists(file_path):
            try:
                tools_logger.info(f"[ARTIFACT] Saving file artifact: {file_path} (type: {artifact_type})")
                artifact_info = _save_file_as_artifact(
                    tool_context=tool_context,
                    file_path=file_path,
                    tool_name=tool_name,
                    artifact_type=artifact_type
                )
                if artifact_info:
                    artifacts_created.append(artifact_info)
                    tools_logger.info(f"[ARTIFACT] ✅ Saved file artifact '{artifact_info.get('filename', file_path)}' for tool '{tool_name}'")
                else:
                    tools_logger.warning(f"[ARTIFACT] ⚠ No artifact info returned for {file_path}")
            except Exception as e:
                tools_logger.error(f"[ARTIFACT] ✗ Failed to save file artifact {file_path}: {e}")
                logger.warning(f"[ARTIFACT] Failed to save {file_path}: {e}")
    
    # 3. Create JSON summary artifact if result contains structured data
    if result.get("status") == "success" and (result.get("metrics") or result.get("overview")):
        try:
            summary_artifact = _create_summary_artifact(
                tool_context=tool_context,
                result=result,
                tool_name=tool_name
            )
            if summary_artifact:
                artifacts_created.append(summary_artifact)
        except Exception as e:
            logger.debug(f"[ARTIFACT] Failed to create summary artifact: {e}")
    
    # 4. Update result with artifact information
    if artifacts_created:
        if "artifacts" not in result:
            result["artifacts"] = []
        
        # Add artifact metadata
        result["artifacts"].extend([
            {
                "filename": a["filename"],
                "type": a["type"],
                "version": a["version"],
                "description": a.get("description", "")
            }
            for a in artifacts_created
        ])
        
        # Add artifact placeholders hint for LLM
        artifact_names = [a["filename"] for a in artifacts_created]
        result["artifact_placeholders"] = {
            f"{{artifact.{name}}}": f"Content of {name}" 
            for name in artifact_names
        }
        
        tools_logger.info(f"[ARTIFACT] ✅ Created {len(artifacts_created)} artifact(s) for tool '{tool_name}': {', '.join(artifact_names)}")
        logger.info(f"[ARTIFACT] Created {len(artifacts_created)} artifact(s) for {tool_name}")
    
    return result


def _extract_file_paths(result: Dict[str, Any]) -> List[tuple]:
    """
    Extract file paths from tool result dictionary.
    
    Returns:
        List of (file_path, artifact_type) tuples
    """
    file_paths = []
    
    # Common keys that contain file paths
    path_keys = {
        "model_path": "model",
        "model_paths": "model",
        "report_path": "report",
        "report_paths": "report",
        "pdf_path": "report",
        "plot_path": "plot",
        "plot_paths": "plot",
        "image_paths": "plot",
        "metrics_path": "metrics",
        "metrics_paths": "metrics",
        "data_path": "data",
        "csv_path": "data",
        "index_path": "index",
        "artifact": "other",
        "artifacts": "other"
    }
    
    for key, artifact_type in path_keys.items():
        value = result.get(key)
        if value:
            if isinstance(value, str) and os.path.exists(value):
                file_paths.append((value, artifact_type))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and os.path.exists(item):
                        file_paths.append((item, artifact_type))
                    elif isinstance(item, dict) and "path" in item:
                        path = item.get("path")
                        if isinstance(path, str) and os.path.exists(path):
                            file_paths.append((path, item.get("type", artifact_type)))
    
    # Extract from artifacts list if present
    artifacts = result.get("artifacts", [])
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, dict):
                path = artifact.get("path")
                if path and os.path.exists(path):
                    file_paths.append((path, artifact.get("type", "other")))
            elif isinstance(artifact, str) and os.path.exists(artifact):
                file_paths.append((artifact, "other"))
    
    return file_paths


def _save_file_as_artifact(
    tool_context: Any,
    file_path: str,
    tool_name: str,
    artifact_type: str = "other"
) -> Optional[Dict[str, Any]]:
    """
    Save a file as an ADK artifact.
    
    Args:
        tool_context: ADK ToolContext with save_artifact method
        file_path: Path to file to save
        tool_name: Name of tool (for naming)
        artifact_type: Type of artifact (model, plot, report, etc.)
        
    Returns:
        Dictionary with artifact info or None if failed
    """
    try:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return None
        
        # Generate artifact filename
        artifact_filename = _generate_artifact_filename(path.name, tool_name, artifact_type)
        
        # Read file content
        if path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.pkl', '.joblib']:
            # Binary files
            file_data = path.read_bytes()
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = _get_mime_type_from_suffix(path.suffix)
            
            if types:
                artifact_part = types.Part(
                    inline_data=types.Blob(mime_type=mime_type, data=file_data)
                )
            else:
                # Fallback if google.genai.types not available
                logger.warning(f"[ARTIFACT] google.genai.types not available, skipping binary artifact")
                return None
        else:
            # Text files
            file_data = path.read_text(encoding='utf-8', errors='ignore')
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type:
                mime_type = "text/plain"
            
            if types:
                artifact_part = types.Part(text=file_data)
            else:
                logger.warning(f"[ARTIFACT] google.genai.types not available, skipping text artifact")
                return None
        
        # Save artifact (handle both sync and async)
        version = _save_artifact_safe(tool_context, artifact_filename, artifact_part)
        
        if version is not None:
            return {
                "filename": artifact_filename,
                "type": artifact_type,
                "version": version,
                "original_path": str(path),
                "size": path.stat().st_size,
                "description": f"{artifact_type} artifact from {tool_name}"
            }
        
    except Exception as e:
        logger.error(f"[ARTIFACT] Error saving file {file_path} as artifact: {e}", exc_info=True)
    
    return None


def _create_summary_artifact(
    tool_context: Any,
    result: Dict[str, Any],
    tool_name: str
) -> Optional[Dict[str, Any]]:
    """
    Create a JSON summary artifact from tool result for LLM accessibility.
    
    This allows prompts to reference: {artifact.{tool_name}_summary.json}
    
    Args:
        tool_context: ADK ToolContext
        result: Tool result dictionary
        tool_name: Name of tool
        
    Returns:
        Dictionary with artifact info or None
    """
    try:
        # Create summary JSON
        summary = {
            "tool": tool_name,
            "status": result.get("status", "unknown"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": result.get("message", ""),
            "metrics": result.get("metrics", {}),
            "overview": result.get("overview", {}),
            "shape": result.get("shape"),
            "columns": result.get("columns"),
            "artifact_placeholders": result.get("artifact_placeholders", {})
        }
        
        # Remove None values
        summary = {k: v for k, v in summary.items() if v is not None}
        
        artifact_filename = f"{tool_name}_summary.json"
        summary_json = json.dumps(summary, indent=2, default=str)
        
        if types:
            artifact_part = types.Part(
                text=summary_json,
                inline_data=types.Blob(mime_type="application/json", data=summary_json.encode('utf-8'))
            )
            
            version = _save_artifact_safe(tool_context, artifact_filename, artifact_part)
            
            if version is not None:
                return {
                    "filename": artifact_filename,
                    "type": "metrics",
                    "version": version,
                    "description": f"Summary of {tool_name} execution"
                }
        else:
            logger.warning(f"[ARTIFACT] google.genai.types not available, skipping summary artifact")
            
    except Exception as e:
        logger.debug(f"[ARTIFACT] Error creating summary artifact: {e}")
    
    return None


def _save_artifact_safe(tool_context: Any, filename: str, artifact_part: Any) -> Optional[int]:
    """
    Safely save artifact handling both sync and async save_artifact methods.
    
    Args:
        tool_context: ADK ToolContext
        filename: Artifact filename
        artifact_part: google.genai.types.Part object
        
    Returns:
        Version number or None if failed
    """
    if not hasattr(tool_context, 'save_artifact'):
        return None
    
    try:
        # Check if save_artifact is async
        if inspect.iscoroutinefunction(tool_context.save_artifact):
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        return executor.submit(
                            lambda: asyncio.run(tool_context.save_artifact(filename=filename, artifact=artifact_part))
                        ).result(timeout=15)
            except RuntimeError:
                pass

            return asyncio.run(tool_context.save_artifact(filename=filename, artifact=artifact_part))
        else:
            # Synchronous version
            return tool_context.save_artifact(filename=filename, artifact=artifact_part)
    except Exception as e:
        logger.warning(f"[ARTIFACT] Failed to save artifact {filename}: {e}")
        return None


def _generate_artifact_filename(original_name: str, tool_name: str, artifact_type: str) -> str:
    """
    Generate a clean artifact filename.
    
    Args:
        original_name: Original filename
        tool_name: Name of tool
        artifact_type: Type of artifact
        
    Returns:
        Clean artifact filename
    """
    # Clean tool name
    clean_tool = tool_name.replace("_tool", "").replace("_", "-")
    
    # Clean original name
    path = Path(original_name)
    stem = path.stem
    suffix = path.suffix
    
    # Generate filename: {tool_name}_{type}_{stem}{suffix}
    if artifact_type == "other":
        return f"{clean_tool}_{stem}{suffix}"
    else:
        return f"{clean_tool}_{artifact_type}_{stem}{suffix}"


def _get_mime_type_from_suffix(suffix: str) -> str:
    """Get MIME type from file suffix."""
    mime_map = {
        '.pkl': 'application/octet-stream',
        '.joblib': 'application/octet-stream',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.pdf': 'application/pdf',
        '.json': 'application/json',
        '.csv': 'text/csv',
        '.md': 'text/markdown',
        '.txt': 'text/plain',
    }
    return mime_map.get(suffix.lower(), 'application/octet-stream')


def list_artifacts_for_llm(tool_context: Any) -> List[str]:
    """
    List available artifacts for LLM awareness.
    
    This mimics ADK's LoadArtifactsTool pattern - lists artifacts
    that can be referenced in prompts using {artifact.filename} syntax.
    
    Args:
        tool_context: ADK ToolContext
        
    Returns:
        List of artifact filenames
    """
    if not tool_context or not hasattr(tool_context, 'list_artifacts'):
        return []
    
    try:
        if inspect.iscoroutinefunction(tool_context.list_artifacts):
            try:
                loop = asyncio.get_running_loop()
                artifacts = asyncio.run_coroutine_threadsafe(
                    tool_context.list_artifacts(),
                    loop
                ).result(timeout=5)
            except RuntimeError:
                artifacts = asyncio.run(tool_context.list_artifacts())
        else:
            artifacts = tool_context.list_artifacts()
        
        if isinstance(artifacts, list):
            return [str(a) for a in artifacts]
        elif isinstance(artifacts, dict):
            return list(artifacts.keys())
    except Exception as e:
        logger.debug(f"[ARTIFACT] Failed to list artifacts: {e}")
    
    return []


def create_artifact_awareness_instruction(tool_context: Any) -> str:
    """
    Create system instruction text for LLM awareness of artifacts.
    
    This follows ADK's LoadArtifactsTool pattern - informs LLM about
    available artifacts and how to reference them.
    
    Args:
        tool_context: ADK ToolContext
        
    Returns:
        Instruction text for LLM
    """
    artifacts = list_artifacts_for_llm(tool_context)
    
    if not artifacts:
        return ""
    
    instruction = f"""
You have access to the following artifacts in this session:
{', '.join(f'"{a}"' for a in artifacts)}

You can reference artifact content in your responses using placeholders like:
{{artifact.{artifacts[0]}}} for the content of {artifacts[0]}

When asked about these artifacts, you can directly reference their content using the placeholder syntax.
"""
    
    return instruction.strip()

