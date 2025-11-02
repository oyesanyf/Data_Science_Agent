"""
Universal tool guard pattern - ensures ALL tools save artifacts like plot() does.

This module provides a reusable guard pattern that:
1. Ensures workspace exists
2. Calls the underlying tool
3. Collects artifact paths from result
4. Saves artifacts to ADK with proper folder structure
5. Creates metadata even if ADK save fails
6. Returns user-friendly success message

Usage:
    @async_sync_safe
    async def my_tool_guard(tool_context=None, **kwargs):
        return await universal_tool_guard(
            tool_name="my_tool",
            inner_tool=my_tool_inner,
            artifact_type="report",  # or "plot", "model", "data", etc.
            artifact_dir="reports",  # or "plots", "models", "data", etc.
            artifact_extension=".md",  # or ".png", ".json", etc.
            tool_context=tool_context,
            kwargs=kwargs,
            discover_artifacts_fn=lambda state: _discover_files(state, "reports/*.md"),
        )
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from . import artifact_manager
from .large_data_config import UPLOAD_ROOT
from .utils.artifacts_io import save_path_as_artifact
from .universal_async_sync_helper import async_sync_safe

logger = logging.getLogger(__name__)


def _exists(path) -> bool:
    """Check if a file path exists."""
    try:
        return Path(path).exists() if path else False
    except Exception:
        return False


def _add_navigation_reminder(result: Dict[str, Any], tool_context: Optional[Any]) -> Dict[str, Any]:
    """
    Add navigation reminder to tool result message.
    Reminds users to use next_stage() or back_stage() to navigate.
    """
    state = getattr(tool_context, "state", {}) if tool_context else {}
    current_stage = state.get("workflow_stage", 1)
    
    # Get next and previous stage numbers
    next_stage_num = (current_stage % 11) + 1
    prev_stage_num = ((current_stage - 2) % 11) + 1
    
    navigation_reminder = (
        f"\n\n---\n"
        f"🧭 **Navigation:** Use `next_stage()` to advance to Stage {next_stage_num} "
        f"or `back_stage()` to return to Stage {prev_stage_num}."
    )
    
    # Append to all display fields
    for field in ["__display__", "message", "text", "ui_text", "content", "display", "_formatted_output"]:
        if field in result and isinstance(result[field], str):
            result[field] = result[field] + navigation_reminder
    
    return result


@async_sync_safe
async def universal_tool_guard(
    tool_name: str,
    inner_tool: Callable,
    artifact_type: str = "other",
    artifact_dir: str = "reports",
    artifact_extension: str = ".md",
    tool_context: Optional[Any] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    discover_artifacts_fn: Optional[Callable[[Dict], List[str]]] = None,
    result_artifact_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Universal guard wrapper for any tool that creates artifacts.
    
    Args:
        tool_name: Name of the tool (for logging and display)
        inner_tool: The actual tool function to call
        artifact_type: Type of artifact ("plot", "report", "model", "data", "other")
        artifact_dir: Workspace subdirectory where artifacts are saved ("plots", "reports", "models", "data")
        artifact_extension: File extension to look for (".png", ".md", ".json", etc.)
        tool_context: ADK tool context
        kwargs: Arguments to pass to inner_tool
        discover_artifacts_fn: Optional function to discover artifacts from workspace state
        result_artifact_keys: List of keys in result dict that contain artifact paths (default: ["artifacts", f"{artifact_type}s"])
    
    Returns:
        Result dict with artifacts, metadata, and user-friendly message
    """
    if kwargs is None:
        kwargs = {}
    
    logger.info("=" * 80)
    logger.info(f"[{tool_name.upper()} GUARD] Starting")
    logger.info(f"[{tool_name.upper()} GUARD] kwargs: {kwargs}")
    
    state = getattr(tool_context, "state", {}) if tool_context else {}
    
    # 1. Ensure workspace exists
    try:
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception:
            pass
        artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
        logger.info(f"[{tool_name.upper()} GUARD] Workspace ensured: {state.get('workspace_root')}")
    except Exception as e:
        logger.error(f"[{tool_name.upper()} GUARD] [X] Failed to ensure workspace: {e}", exc_info=True)
        return {
            "status": "failed",
            "message": f"Failed to initialize workspace: {e}",
            "artifacts": [],
        }
    
    # 2. Call the underlying tool
    try:
        logger.info(f"[{tool_name.upper()} GUARD] Calling {tool_name}...")
        if hasattr(inner_tool, '__call__'):
            # Check if it's async
            import inspect
            if inspect.iscoroutinefunction(inner_tool):
                result = await inner_tool(tool_context=tool_context, **kwargs)
            else:
                result = inner_tool(tool_context=tool_context, **kwargs)
        else:
            result = inner_tool(tool_context=tool_context, **kwargs)
        logger.info(f"[{tool_name.upper()} GUARD] {tool_name} returned: {type(result)}, keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    except Exception as e:
        logger.error(f"[{tool_name.upper()} GUARD] [X] {tool_name} failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "message": f"{tool_name} failed: {e}",
            "artifacts": [],
        }
    
    state = getattr(tool_context, "state", {}) if tool_context else {}
    
    # 3. Collect artifact paths from result
    if result_artifact_keys is None:
        result_artifact_keys = ["artifacts", f"{artifact_type}s", f"{artifact_type}_paths"]
    
    returned = []
    if isinstance(result, dict):
        for key in result_artifact_keys:
            arts = result.get(key, [])
            if arts:
                logger.info(f"[{tool_name.upper()} GUARD] Found {len(arts)} artifacts in result[{key}]")
                for a in arts:
                    if isinstance(a, dict):
                        p = a.get("path") or a.get("filename") or str(a)
                    else:
                        p = str(a) if a else None
                    
                    if p:
                        p_abs = Path(p).resolve() if not Path(p).is_absolute() else Path(p)
                        if _exists(p_abs):
                            returned.append(str(p_abs))
                            logger.info(f"[{tool_name.upper()} GUARD] ✅ Added artifact from result: {p_abs}")
                        else:
                            logger.warning(f"[{tool_name.upper()} GUARD] ⚠️ Artifact path doesn't exist: {p_abs}")
    
    logger.info(f"[{tool_name.upper()} GUARD] Collected {len(returned)} files from result")
    
    # 4. Use discovery as fallback if no files in result
    if not returned and discover_artifacts_fn:
        logger.info(f"[{tool_name.upper()} GUARD] No files in result, trying discovery...")
        discovered = discover_artifacts_fn(state)
        logger.info(f"[{tool_name.upper()} GUARD] Discovered {len(discovered)} files from workspace")
        created_files = discovered
    else:
        created_files = returned
    
    # 5. Register and save artifacts to ADK
    shown_names = []
    artifact_metadata = []
    
    for f in created_files:
        if not Path(f).exists():
            logger.warning(f"[{tool_name.upper()} GUARD] Skipping non-existent file: {f}")
            continue
        
        try:
            # Register in local workspace tracking
            artifact_manager.register_artifact(state, f, kind=artifact_type, label=Path(f).stem)
        except Exception as e:
            logger.warning(f"[{tool_name.upper()} GUARD] Failed to register artifact locally: {e}")
        
        # Save to ADK ArtifactService with folder structure prefix
        filename_only = Path(f).name
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                artifact_filename = f"{artifact_dir}/{filename_only}"
                logger.info(f"[{tool_name.upper()} GUARD] Saving {artifact_filename} to ADK ArtifactService...")
                art_info = await save_path_as_artifact(
                    tool_context,
                    f,
                    filename=artifact_filename,
                    user_scope=False
                )
                shown_names.append(filename_only)
                artifact_metadata.append(art_info)
                logger.info(f"[{tool_name.upper()} GUARD] [OK] Saved artifact: {art_info['filename']} v{art_info['version']}")
            except Exception as e:
                logger.warning(f"[{tool_name.upper()} GUARD] Failed to save to ADK: {e}")
                # Even if save fails, include the filename (file exists on disk and may be in ADK already)
                shown_names.append(filename_only)
        else:
            logger.warning(f"[{tool_name.upper()} GUARD] No save_artifact method available on context")
            shown_names.append(filename_only)
    
    # 6. Ensure metadata exists for all shown files (handles case where artifacts saved but metadata missing)
    if shown_names:
        logger.info(f"[{tool_name.upper()} GUARD] Found {len(shown_names)} files, ensuring metadata exists for all")
        for i, name in enumerate(shown_names):
            if i >= len(artifact_metadata):
                artifact_metadata.append({
                    "filename": f"{artifact_dir}/{name}",
                    "version": 1,
                    "source": "disk_or_adk"
                })
                logger.info(f"[{tool_name.upper()} GUARD] Created metadata for {name}")
    
    # 7. Build result with user-friendly message
    if not isinstance(result, dict):
        result = {}
    
    result.setdefault("status", "success")
    result["artifacts"] = artifact_metadata
    result["artifact_count"] = len(artifact_metadata)
    
    # Build user-friendly message
    if shown_names and (artifact_metadata or created_files):
        message_parts = [f"✅ **{tool_name.replace('_', ' ').title()} Complete**\n"]
        message_parts.append(f"**Generated {len(shown_names)} artifact{'s' if len(shown_names) > 1 else ''}:**\n")
        for i, name in enumerate(shown_names, 1):
            meta = artifact_metadata[i-1] if i-1 < len(artifact_metadata) else {}
            version_info = f" (v{meta.get('version', 1)})" if meta.get('version') else ""
            message_parts.append(f"{i}. **{name}**{version_info}")
        message_parts.append(f"\n💡 **View:** Check the Artifacts panel to see your files!")
        formatted_message = "\n".join(message_parts)
    else:
        logger.warning(f"[{tool_name.upper()} GUARD] ⚠️ No artifacts found!")
        formatted_message = (
            f"⚠️ **{tool_name.replace('_', ' ').title()} Issue:**\n\n"
            f"No artifacts were found or saved.\n\n"
            f"**Check logs for detailed diagnostics.**"
        )
        result["status"] = "warning"
    
    # Set all display fields
    result["__display__"] = formatted_message
    result["text"] = formatted_message
    result["message"] = formatted_message
    result["ui_text"] = formatted_message
    result["content"] = formatted_message
    result["display"] = formatted_message
    result["_formatted_output"] = formatted_message
    
    # Add navigation reminder after tool completion
    result = _add_navigation_reminder(result, tool_context)
    
    # CRITICAL: Ensure markdown artifact is saved for UI indexing (like safe_tool_wrapper does)
    # This prevents 404 errors when the UI tries to load tool_executions/*.md files
    try:
        from .agent import _save_tool_markdown_artifact, _extract_display_text
        display_text = _extract_display_text(result)
        md_filename = _save_tool_markdown_artifact(tool_name, display_text, tool_context)
        # Add to artifacts list so it's discoverable
        if isinstance(result, dict):
            result.setdefault("artifacts", []).append(md_filename)
            result.setdefault("artifact_paths", []).append(md_filename)
            result.setdefault("files", []).append(md_filename)
        logger.info(f"[{tool_name.upper()} GUARD] ✅ Saved markdown artifact: {md_filename}")
    except Exception as md_error:
        logger.warning(f"[{tool_name.upper()} GUARD] Failed to save markdown artifact: {md_error}")
    
    logger.info(f"[{tool_name.upper()} GUARD] [OK] Complete. Generated {len(created_files)} files, saved {len(artifact_metadata)} to ArtifactService")
    logger.info("=" * 80)
    
    return result

