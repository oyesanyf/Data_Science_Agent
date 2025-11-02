"""
ADK tools for listing and loading artifacts.
These allow the agent to discover and work with saved artifacts.
"""
import logging
from typing import Any, Dict, Optional
from google.genai import types
from ..ds_tools import ensure_display_fields

logger = logging.getLogger(__name__)


@ensure_display_fields
async def list_artifacts_tool(tool_context) -> Dict[str, Any]:
    """
    Lists all available artifacts in the current session/user scope.
    
    Returns:
        {"status": "success", "files": [...]} or error dict
    """
    logger.info("[ARTIFACTS TOOL] Listing artifacts")
    try:
        if not hasattr(tool_context, "list_artifacts"):
            return {
                "status": "failed",
                "error": "ArtifactService not configured. Add artifact_service to Runner."
            }
        
        files = await tool_context.list_artifacts()
        if not files:
            # Fallback: scan workspace on disk if registry is empty
            try:
                state = getattr(tool_context, "state", {}) or {}
                ws = state.get("workspace_paths", {}) or {}
                
                # Try to recover workspace if missing
                if not ws or not state.get("workspace_root"):
                    from data_science.artifact_manager import _try_recover_workspace_state
                    if _try_recover_workspace_state(state):
                        ws = state.get("workspace_paths", {}) or {}
                        logger.info("[list_artifacts_tool] [OK] Workspace recovered from disk")
                
                candidates = []
                import os
                for k in ("uploads", "derived", "reports", "models", "plots", "artifacts"):
                    d = ws.get(k)
                    if d and os.path.isdir(d):
                        for root, _, filenames in os.walk(d):
                            for fname in filenames:
                                candidates.append(os.path.join(root, fname))
                files = candidates
                logger.info(f"[ARTIFACTS TOOL] Fallback scan found {len(files)} artifacts")
            except Exception as e:
                logger.warning(f"[ARTIFACTS TOOL] Fallback scan failed: {e}")

        logger.info(f"[ARTIFACTS TOOL] Found {len(files or [])} artifacts")

        return {
            "status": "success",
            "files": files or [],
            "count": len(files or []),
            "message": f" Found {len(files or [])} artifact(s)",
            "ui_text": f" Found {len(files or [])} artifact(s):\n" + "\n".join(f"- {f}" for f in (files or [])[:20])
        }
    except Exception as e:
        logger.error(f"[ARTIFACTS TOOL] [X] Failed to list artifacts: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


@ensure_display_fields
async def load_artifact_text_preview_tool(
    tool_context,
    filename: str,
    version: Optional[int] = None
) -> Dict[str, Any]:
    """
    Loads an artifact (latest if version=None) and returns first 4KB as text preview.
    
    Automatically falls back to filesystem if ADK artifact service is not available.
    
    Args:
        tool_context: ADK callback context
        filename: Artifact filename to load (can be full path or just filename)
        version: Specific version (None = latest, ignored for filesystem fallback)
    
    Returns:
        {"status": "success", "preview": <text>, ...} or error dict
    """
    logger.info(f"[ARTIFACTS TOOL] Loading artifact preview: {filename} (version={version})")
    
    data = None
    mime = "unknown"
    source = "adk"
    
    # TRY 1: ADK artifact service (primary)
    try:
        if hasattr(tool_context, "load_artifact"):
            part = await tool_context.load_artifact(filename=filename, version=version)
            
            if part and part.inline_data:
                data = part.inline_data.data or b""
                mime = part.inline_data.mime_type or "unknown"
                logger.info(f"[ARTIFACTS TOOL] ✅ Loaded from ADK: {filename} ({len(data)} bytes)")
            else:
                logger.warning(f"[ARTIFACTS TOOL] ADK returned empty for: {filename}")
        else:
            logger.warning(f"[ARTIFACTS TOOL] ADK artifact service not configured")
    except Exception as adk_err:
        logger.warning(f"[ARTIFACTS TOOL] ADK load failed for {filename}: {adk_err}")
    
    # TRY 2: Filesystem fallback (if ADK failed)
    if data is None:
        logger.info(f"[ARTIFACTS TOOL] FALLBACK: Trying filesystem load for {filename}")
        try:
            from pathlib import Path
            import mimetypes
            
            # Get workspace root from state
            state = getattr(tool_context, "state", {}) or {}
            workspace_root = state.get("workspace_root")
            
            if not workspace_root:
                logger.warning(f"[ARTIFACTS TOOL] No workspace_root in state, cannot load from filesystem")
            else:
                # Try multiple locations
                search_paths = []
                
                # If filename is already a full path, try it directly
                if Path(filename).is_absolute():
                    search_paths.append(Path(filename))
                else:
                    # Search in common folders
                    ws_root = Path(workspace_root)
                    for folder in ["reports", "results", "plots", "models", "data", "uploads"]:
                        search_paths.append(ws_root / folder / filename)
                        # Also try with subfolder prefix removed (e.g., "reports/xxx.md" → "xxx.md")
                        if "/" in filename:
                            search_paths.append(ws_root / folder / Path(filename).name)
                
                # Try each path
                for path in search_paths:
                    if path.exists() and path.is_file():
                        data = path.read_bytes()
                        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                        source = "filesystem"
                        logger.info(f"[ARTIFACTS TOOL] ✅ FALLBACK SUCCESS: Loaded from filesystem: {path} ({len(data)} bytes)")
                        break
                
                if data is None:
                    logger.warning(f"[ARTIFACTS TOOL] File not found in filesystem: {filename}")
                    logger.warning(f"[ARTIFACTS TOOL] Searched: {[str(p) for p in search_paths]}")
        
        except Exception as fs_err:
            logger.error(f"[ARTIFACTS TOOL] Filesystem fallback failed: {fs_err}", exc_info=True)
    
    # FINAL: Return result or error
    if data is None:
        return {
            "status": "failed",
            "error": f"Artifact '{filename}' not found in ADK service or filesystem"
        }
    
    # Safe text preview
    preview = ""
    if data:
        try:
            preview = data[:4096].decode("utf-8", errors="replace")
        except Exception:
            preview = f"[Binary data, {len(data)} bytes, cannot preview as text]"
    
    logger.info(f"[ARTIFACTS TOOL] ✅ Loaded {filename}: {len(data)} bytes, mime={mime}, source={source}")
    
    return {
        "status": "success",
        "filename": filename,
        "mime_type": mime,
        "bytes": len(data),
        "preview": preview,
        "source": source,  # NEW: Track where file came from
        "message": f"✅ Loaded artifact: **{filename}** ({len(data)} bytes, {mime}) [source: {source}]",
        "ui_text": f"✅ Loaded artifact: **{filename}**\n- Size: {len(data)} bytes\n- Type: {mime}\n- Source: {source}\n\n**Preview:**\n```\n{preview[:500]}\n```"
    }


@ensure_display_fields
async def download_artifact_tool(
    tool_context,
    filename: str,
    output_path: str,
    version: Optional[int] = None
) -> Dict[str, Any]:
    """
    Downloads an artifact to a local file path.
    
    Automatically falls back to filesystem copy if ADK artifact service is not available.
    
    Args:
        tool_context: ADK callback context
        filename: Artifact filename to download (can be full path or just filename)
        output_path: Local path to save to
        version: Specific version (None = latest, ignored for filesystem fallback)
    
    Returns:
        {"status": "success", "path": <output_path>} or error dict
    """
    logger.info(f"[ARTIFACTS TOOL] Downloading artifact: {filename} → {output_path}")
    
    data = None
    source = "adk"
    
    # TRY 1: ADK artifact service (primary)
    try:
        if hasattr(tool_context, "load_artifact"):
            part = await tool_context.load_artifact(filename=filename, version=version)
            
            if part and part.inline_data:
                data = part.inline_data.data or b""
                logger.info(f"[ARTIFACTS TOOL] ✅ Downloaded from ADK: {filename} ({len(data)} bytes)")
            else:
                logger.warning(f"[ARTIFACTS TOOL] ADK returned empty for: {filename}")
        else:
            logger.warning(f"[ARTIFACTS TOOL] ADK artifact service not configured")
    except Exception as adk_err:
        logger.warning(f"[ARTIFACTS TOOL] ADK download failed for {filename}: {adk_err}")
    
    # TRY 2: Filesystem fallback (if ADK failed)
    if data is None:
        logger.info(f"[ARTIFACTS TOOL] FALLBACK: Trying filesystem copy for {filename}")
        try:
            from pathlib import Path
            
            # Get workspace root from state
            state = getattr(tool_context, "state", {}) or {}
            workspace_root = state.get("workspace_root")
            
            if not workspace_root:
                logger.warning(f"[ARTIFACTS TOOL] No workspace_root in state, cannot copy from filesystem")
            else:
                # Try multiple locations
                search_paths = []
                
                # If filename is already a full path, try it directly
                if Path(filename).is_absolute():
                    search_paths.append(Path(filename))
                else:
                    # Search in common folders
                    ws_root = Path(workspace_root)
                    for folder in ["reports", "results", "plots", "models", "data", "uploads"]:
                        search_paths.append(ws_root / folder / filename)
                        # Also try with subfolder prefix removed (e.g., "reports/xxx.md" → "xxx.md")
                        if "/" in filename:
                            search_paths.append(ws_root / folder / Path(filename).name)
                
                # Try each path
                for path in search_paths:
                    if path.exists() and path.is_file():
                        data = path.read_bytes()
                        source = "filesystem"
                        logger.info(f"[ARTIFACTS TOOL] ✅ FALLBACK SUCCESS: Found in filesystem: {path} ({len(data)} bytes)")
                        break
                
                if data is None:
                    logger.warning(f"[ARTIFACTS TOOL] File not found in filesystem: {filename}")
        
        except Exception as fs_err:
            logger.error(f"[ARTIFACTS TOOL] Filesystem fallback failed: {fs_err}", exc_info=True)
    
    # FINAL: Write to output or error
    if data is None:
        return {
            "status": "failed",
            "error": f"Artifact '{filename}' not found in ADK service or filesystem"
        }
        
    # Write to disk
    try:
        from pathlib import Path
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        
        logger.info(f"[ARTIFACTS TOOL] ✅ Downloaded {filename} to {output_path} ({len(data)} bytes) [source: {source}]")
        
        return {
            "status": "success",
            "filename": filename,
            "path": str(output),
            "bytes": len(data),
            "source": source,  # NEW: Track where file came from
            "message": f"⬇ Downloaded artifact: **{filename}** to `{output_path}` ({len(data)} bytes) [source: {source}]",
            "ui_text": f"⬇ Downloaded artifact: **{filename}**\n- Saved to: `{output_path}`\n- Size: {len(data)} bytes\n- Source: {source}"
        }
    except Exception as e:
        logger.error(f"[ARTIFACTS TOOL] ❌ Failed to write file: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}


@ensure_display_fields
async def repair_session_tool(tool_context) -> Dict[str, Any]:
    """
    Heal a running session by rehydrating state and re-registering any CSV
    found under the workspace uploads directory. Mirrors to ADK artifacts panel.
    """
    try:
        state = getattr(tool_context, "state", {}) or {}
        # Rehydrate baseline state
        try:
            from data_science import artifact_manager as _am
            _am.rehydrate_session_state(state)
        except Exception as e:
            logger.warning(f"[repair_session_tool] rehydrate failed: {e}")
        
        # Try recovery if workspace still missing
        ws = state.get("workspace_paths", {}) or {}
        if not ws or not state.get("workspace_root"):
            from data_science.artifact_manager import _try_recover_workspace_state
            if _try_recover_workspace_state(state):
                ws = state.get("workspace_paths", {}) or {}
                logger.info("[repair_session_tool] [OK] Workspace recovered from disk")

        uploads = ws.get("uploads")
        repaired = []
        if uploads and __import__('os').path.isdir(uploads):
            import os
            for fname in sorted(os.listdir(uploads)):
                p = os.path.join(uploads, fname)
                if fname.lower().endswith(".csv"):
                    try:
                        from data_science import artifact_manager as _am
                        _am.register_and_sync_artifact(tool_context, p, kind="upload", label="raw_upload")
                        repaired.append(p)
                    except Exception:
                        pass
                # CSV only - Parquet support removed

        return {
            "status": "success" if repaired else "noop",
            "message": f"Repaired {len(repaired)} artifacts." if repaired else "Nothing to repair.",
            "paths": repaired,
        }
    except Exception as e:
        logger.error(f"[ARTIFACTS TOOL] [X] Failed to repair session: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}

