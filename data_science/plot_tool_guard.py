"""
Hardened plot tool guard to ensure plots appear in UI artifacts panel.
Uses ADK's native ArtifactService for proper integration.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List
from . import artifact_manager
from .large_data_config import UPLOAD_ROOT
# Import plot_tool from agent.py (working implementation)
try:
    from .agent import plot_tool as _plot_inner
except ImportError:
    # Fallback to adk_safe_wrappers if agent.py doesn't have it
    from .adk_safe_wrappers import plot_tool as _plot_inner
from .universal_async_sync_helper import async_sync_safe
# Import intelligent retry from agent.py
try:
    from .agent import _intelligent_retry
except ImportError:
    # Fallback: simple retry function
    def _intelligent_retry(func, max_retries=3, base_delay=0.5, backoff_factor=2.0, retryable_exceptions=(Exception,)):
        import time
        for attempt in range(max_retries):
            try:
                return func()
            except retryable_exceptions as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (backoff_factor ** attempt)
                    logger.warning(f"[RETRY] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"[RETRY] All {max_retries} attempts failed. Last error: {e}")
        return None

logger = logging.getLogger(__name__)

def _exists(path) -> bool:
    """Check if a file path exists."""
    try:
        return Path(path).exists() if path else False
    except Exception:
        return False

def _discover_created_pngs(state: dict) -> List[str]:
    ws = (state or {}).get("workspace_paths", {}) or {}
    plots_dir = ws.get("plots")
    if not plots_dir or not Path(plots_dir).exists():
        return []
    # newest first, limit to a reasonable count
    return [str(p) for p in sorted(Path(plots_dir).glob("*.png"),
                                   key=lambda x: x.stat().st_mtime,
                                   reverse=True)[:50]]

@async_sync_safe
async def plot_tool_guard(tool_context=None, **kwargs):
    """
    Wraps plot_tool to ensure:
    - files are registered in workspace
    - files are pushed to Artifacts pane
    - user gets a friendly chat message
    
    [WARNING] MUST BE ASYNC to await the underlying plot_tool!
    """
    logger.info("=" * 80)
    logger.info("[PLOT GUARD] Starting plot generation")
    logger.info(f"[PLOT GUARD] kwargs: {kwargs}")
    
    state = getattr(tool_context, "state", {}) if tool_context else {}
    
    # Rehydrate + ensure workspace BEFORE calling plot tool
    try:
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception:
            pass
        artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
        logger.info(f"[PLOT GUARD] Workspace ensured: {state.get('workspace_root')}")
    except Exception as e:
        logger.error(f"[PLOT GUARD] [X] Failed to ensure workspace: {e}", exc_info=True)
        return {
            "status": "failed",
            "message": f"Failed to initialize workspace: {e}",
            "artifacts": [],
        }
    
    # [WARNING] CRITICAL: AWAIT the async plot_tool!
    try:
        logger.info("[PLOT GUARD] Calling plot_tool (async)...")
        result = await _plot_inner(tool_context=tool_context, **kwargs)
        logger.info(f"[PLOT GUARD] plot_tool returned: {type(result)}, keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    except Exception as e:
        logger.error(f"[PLOT GUARD] [X] plot_tool failed: {e}", exc_info=True)
        return {
            "status": "failed",
            "message": f"Plot generation failed: {e}",
            "artifacts": [],
        }

    state = getattr(tool_context, "state", {}) if tool_context else {}

    # CRITICAL FIX: Gather any paths the inner tool already returned
    # plot_tool returns artifacts as list of file paths (strings)
    returned = []
    if isinstance(result, dict):
        # Check multiple possible keys where artifacts might be stored
        arts = result.get("artifacts") or result.get("plots") or result.get("plot_paths") or []
        logger.info(f"[PLOT GUARD] Found {len(arts)} artifacts in result: {type(arts)}")
        
        for a in arts:
            # Handle both dict format {"path": "...", ...} and string format "path/to/file.png"
            if isinstance(a, dict):
                p = a.get("path") or a.get("filename") or str(a)
            else:
                p = str(a) if a else None
            
            if p:
                # Convert to absolute path if relative
                p_abs = Path(p).resolve() if not Path(p).is_absolute() else Path(p)
                if _exists(p_abs):
                    returned.append(str(p_abs))
                    logger.info(f"[PLOT GUARD] ✅ Added artifact from result: {p_abs}")
                else:
                    logger.warning(f"[PLOT GUARD] ⚠️ Artifact path from result doesn't exist: {p_abs}")
    
    logger.info(f"[PLOT GUARD] Collected {len(returned)} files from result")
    
    # Only use discovery as fallback if no files were returned
    if not returned:
        logger.info("[PLOT GUARD] No files in result, trying discovery...")
        discovered = _discover_created_pngs(state)
        logger.info(f"[PLOT GUARD] Discovered {len(discovered)} files from workspace")
        created_files = discovered
    else:
        created_files = returned

    # Register + push everything using ADK native artifact service
    shown_names = []
    artifact_metadata = []
    
    # CRITICAL: Check if plot() already saved artifacts to ADK (they're in result with "plots/" prefix)
    # If artifacts were already saved by plot(), we don't need to save them again
    already_saved_artifacts = []
    if isinstance(result, dict):
        # Check if result has artifact metadata (from plot() saving to ADK)
        saved_arts = result.get("saved_artifacts") or result.get("artifact_metadata") or []
        if saved_arts:
            logger.info(f"[PLOT GUARD] Found {len(saved_arts)} artifacts already saved by plot()")
            already_saved_artifacts = saved_arts
    
    for f in created_files:
        if not Path(f).exists():
            logger.warning(f"[PLOT GUARD] Skipping non-existent file: {f}")
            continue
        
        try:
            # Register in local workspace tracking (keep local registry consistent)
            artifact_manager.register_artifact(state, f, kind="plot", label=Path(f).stem)
        except Exception as e:
            logger.warning(f"[PLOT GUARD] Failed to register artifact locally: {e}")
        
        # Check if this artifact was already saved by plot()
        filename_only = Path(f).name
        already_saved = any(
            (a.get("filename") or "").endswith(filename_only) or 
            (a.get("filename") or "").endswith(f"plots/{filename_only}")
            for a in already_saved_artifacts
        )
        
        if already_saved:
            logger.info(f"[PLOT GUARD] Artifact {filename_only} already registered, creating filesystem metadata")
            # Create filesystem-based metadata (convert any ADK references to filesystem)
            filesystem_path = str(Path(f).absolute())
            existing_info = {
                "filename": f"plots/{filename_only}",
                "path": filesystem_path,
                "source": "filesystem",
                "exists": True
            }
            shown_names.append(filename_only)
            artifact_metadata.append(existing_info)
        else:
            # DUAL-PATH SAVING: Save to both filesystem AND ADK artifact service with intelligent retry
            shown_names.append(filename_only)
            filesystem_path = str(Path(f).absolute())
            
            # Filesystem metadata (always exists - file is on disk)
            fs_meta = {
                "filename": f"plots/{filename_only}",
                "path": filesystem_path,
                "source": "filesystem",
                "exists": True
            }
            
            # Try to save to ADK artifact service (with retry)
            adk_meta = None
            if tool_context and hasattr(tool_context, "save_artifact"):
                def _save_plot_to_adk():
                    """Inner function for ADK save with retry"""
                    try:
                        from google.genai import types
                        import mimetypes
                        
                        # Read file content
                        file_data = Path(f).read_bytes()
                        mime_type, _ = mimetypes.guess_type(str(f))
                        if not mime_type:
                            mime_type = "image/png"  # Default for plots
                        
                        # Create Part with inline_data Blob
                        artifact_part = types.Part(
                            inline_data=types.Blob(
                                mime_type=mime_type,
                                data=file_data
                            )
                        )
                        
                        # Determine if context.save_artifact is async
                        import inspect
                        artifact_filename = f"plots/{filename_only}"
                        
                        if inspect.iscoroutinefunction(tool_context.save_artifact):
                            # Async context
                            import asyncio
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    # Loop is running - use future
                                    import concurrent.futures
                                    future = concurrent.futures.Future()
                                    async def _async_save():
                                        try:
                                            version = await tool_context.save_artifact(filename=artifact_filename, artifact=artifact_part)
                                            future.set_result(version)
                                        except Exception as e:
                                            future.set_exception(e)
                                    asyncio.create_task(_async_save())
                                    return future.result(timeout=5)
                                else:
                                    return loop.run_until_complete(tool_context.save_artifact(filename=artifact_filename, artifact=artifact_part))
                            except Exception as async_err:
                                logger.warning(f"[PLOT GUARD] Async save failed, trying sync: {async_err}")
                                return tool_context.save_artifact(filename=artifact_filename, artifact=artifact_part)
                        else:
                            # Sync context
                            return tool_context.save_artifact(filename=artifact_filename, artifact=artifact_part)
                    except ImportError:
                        logger.warning(f"[PLOT GUARD] google.genai.types not available")
                        raise
                    except Exception as e:
                        logger.warning(f"[PLOT GUARD] ADK save error: {e}")
                        raise
                
                adk_version = _intelligent_retry(_save_plot_to_adk, max_retries=3, base_delay=0.5, backoff_factor=2.0)
                if adk_version is not None:
                    adk_meta = {
                        "filename": f"plots/{filename_only}",
                        "version": adk_version,
                        "source": "adk",
                        "path": filesystem_path  # Also include filesystem path for reference
                    }
                    logger.info(f"[PLOT GUARD] ✅ ADK service save SUCCESS: plots/{filename_only} v{adk_version}")
                else:
                    logger.warning(f"[PLOT GUARD] ⚠️ ADK service save FAILED after retries (non-critical)")
            
            # Use ADK metadata if available, otherwise filesystem metadata
            artifact_metadata.append(adk_meta if adk_meta else fs_meta)
            logger.info(f"[PLOT GUARD] [OK] Registered artifact: {filename_only} (filesystem: ✅, ADK: {'✅' if adk_meta else '❌'})")

    # CRITICAL FIX: If we found files on disk but artifact_metadata is empty or incomplete, create metadata
    # This handles the case where plot() saved artifacts directly to ADK (they're visible in UI) but metadata wasn't returned
    if shown_names:
        # Ensure metadata exists for all shown files (plot() may have saved them but didn't return metadata)
        logger.info(f"[PLOT GUARD] Found {len(shown_names)} files, ensuring metadata exists for all")
        # Create metadata for any missing entries
        for i, name in enumerate(shown_names):
            if i >= len(artifact_metadata):
                # This file doesn't have metadata yet, but it exists (filesystem-only)
                # Find the actual file path from created_files
                matching_file = next((f for f in created_files if Path(f).name == name), None)
                if matching_file:
                    filesystem_path = str(Path(matching_file).absolute())
                    artifact_metadata.append({
                        "filename": f"plots/{name}",
                        "path": filesystem_path,
                        "source": "filesystem",
                        "exists": True
                    })
                    logger.info(f"[PLOT GUARD] Created filesystem metadata for {name}: {filesystem_path}")
                else:
                    artifact_metadata.append({
                        "filename": f"plots/{name}",
                        "source": "filesystem",
                        "exists": False
                    })
    
    # Normalize the return
    if not isinstance(result, dict):
        result = {}

    result.setdefault("status", "success")
    
    # Include ADK artifact metadata (or disk-based metadata if ADK save failed)
    result["artifacts"] = artifact_metadata  # Now includes {"filename": ..., "version": ...}
    result["artifact_count"] = len(artifact_metadata)
    
    # Build user-friendly message
    if shown_names and (artifact_metadata or created_files):
        message_parts = ["📊 **Plots Generated and Saved to Artifacts:**\n"]
        for i, name in enumerate(shown_names, 1):
            meta = artifact_metadata[i-1] if i-1 < len(artifact_metadata) else {}
            # Filesystem-only: show path if available, no version numbers
            path_info = f" - `{meta.get('path', name)}`" if meta.get('path') else ""
            message_parts.append(f"{i}. **{name}**{path_info}")
        message_parts.append(f"\n✅ **Total:** {len(shown_names)} plot{'s' if len(shown_names) > 1 else ''} saved")
        message_parts.append("\n💡 **View:** Check the Artifacts panel (right side) to see your plots!")
        formatted_message = "\n".join(message_parts)
    else:
        # CRITICAL: If no artifacts found, log detailed diagnostics
        logger.error(f"[PLOT GUARD] ❌ NO ARTIFACTS FOUND!")
        logger.error(f"[PLOT GUARD]   - Files from result: {len(returned)}")
        logger.error(f"[PLOT GUARD]   - Files discovered: {len(_discover_created_pngs(state))}")
        logger.error(f"[PLOT GUARD]   - Created files: {len(created_files)}")
        logger.error(f"[PLOT GUARD]   - Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        if isinstance(result, dict):
            logger.error(f"[PLOT GUARD]   - Result artifacts: {result.get('artifacts', 'N/A')}")
            logger.error(f"[PLOT GUARD]   - Result plots: {result.get('plots', 'N/A')}")
            logger.error(f"[PLOT GUARD]   - Result plot_paths: {result.get('plot_paths', 'N/A')}")
            logger.error(f"[PLOT GUARD]   - Result status: {result.get('status', 'N/A')}")
            logger.error(f"[PLOT GUARD]   - Result rows/cols: {result.get('rows', 'N/A')}/{result.get('cols', 'N/A')}")
        
        # Check workspace paths
        ws_paths = state.get("workspace_paths", {})
        plots_dir = ws_paths.get("plots") if ws_paths else None
        logger.error(f"[PLOT GUARD]   - Workspace plots dir: {plots_dir}")
        logger.error(f"[PLOT GUARD]   - Plots dir exists: {Path(plots_dir).exists() if plots_dir else False}")
        if plots_dir and Path(plots_dir).exists():
            png_files = list(Path(plots_dir).glob("*.png"))
            logger.error(f"[PLOT GUARD]   - PNG files in plots dir: {len(png_files)}")
            if png_files:
                logger.error(f"[PLOT GUARD]   - Most recent PNG: {max(png_files, key=lambda x: x.stat().st_mtime)}")
        
        formatted_message = (
            "⚠️ **Plot Generation Issue:**\n\n"
            "The plot tool reported success but no artifacts were found or saved.\n\n"
            "**Possible causes:**\n"
            "1. Dataset has insufficient data (needs at least 2 numeric columns for plots)\n"
            "2. Plots were generated but not saved to the workspace\n"
            "3. Workspace directory not properly initialized\n"
            "4. File paths not accessible\n\n"
            "**Diagnostics:**\n"
            f"- Artifacts in result: {len(returned)}\n"
            f"- Files discovered: {len(_discover_created_pngs(state))}\n"
            f"- Dataset shape: {result.get('rows', 'N/A')} rows × {result.get('cols', 'N/A')} cols\n\n"
            "**Check logs for detailed diagnostics.**"
        )
        result["status"] = "warning"  # Not complete failure, but incomplete
    
    # [OK] CRITICAL: Add __display__ field for LLM to extract and show in chat
    result["__display__"] = formatted_message  # HIGHEST PRIORITY display field
    result["text"] = formatted_message
    result["message"] = formatted_message
    result["ui_text"] = formatted_message
    result["content"] = formatted_message
    result["display"] = formatted_message
    result["_formatted_output"] = formatted_message
    
    # Add navigation reminder after tool completion
    from .universal_tool_guard import _add_navigation_reminder
    result = _add_navigation_reminder(result, tool_context)
    
    logger.info(f"[PLOT GUARD] [OK] Complete. Generated {len(created_files)} plots, registered {len(artifact_metadata)} filesystem artifacts")
    logger.info(f"[PLOT GUARD] Display message: {formatted_message[:200]}")
    logger.info("=" * 80)
    
    return result
