"""
Executive report guard to ensure PDFs appear in artifacts UI.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict
from data_science import artifact_manager as artifact_manager
from .large_data_config import UPLOAD_ROOT
from .utils.artifacts_io import save_path_as_artifact, announce_artifact

logger = logging.getLogger(__name__)

def _exists(path: str) -> bool:
    """Helper to check if path exists."""
    try:
        return Path(path).exists()
    except Exception:
        return False

async def export_executive_report_tool_guard(tool_context=None, **kwargs) -> Dict[str, Any]:
    """
    Guarantees the executive report PDF is:
    - written under workspace/reports/
    - registered in artifact registry
    - pushed to the Artifacts pane
    - summarized in chat
    """
    logger.info("=" * 80)
    logger.info("[EXEC REPORT GUARD] Starting executive report generation")
    logger.info("=" * 80)
    
    state = getattr(tool_context, "state", {}) if tool_context else {}
    logger.info(f"[EXEC REPORT GUARD] Tool context available: {tool_context is not None}")
    # state might be a State object or dict, handle both
    try:
        state_keys = list(state.keys()) if hasattr(state, 'keys') else dir(state)
        logger.info(f"[EXEC REPORT GUARD] State keys/attrs: {state_keys}")
    except Exception:
        logger.info(f"[EXEC REPORT GUARD] State type: {type(state)}")
    
    try:
        artifact_manager.rehydrate_session_state(state)
    except Exception as e:
        logger.warning(f"[EXEC REPORT GUARD] rehydrate_session_state failed: {e}")
    
    try:
        artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
        logger.info(f"[EXEC REPORT GUARD] Workspace ensured")
    except Exception as e:
        logger.error(f"[EXEC REPORT GUARD] Failed to ensure workspace: {e}")
        # Try recovery
        from .artifact_manager import _try_recover_workspace_state
        if not _try_recover_workspace_state(state):
            logger.error(f"[EXEC REPORT GUARD] [X] Could not recover workspace")
            return {
                "status": "failed",
                "message": "Could not initialize or recover workspace. Please ensure a file is uploaded.",
            }
        logger.info(f"[EXEC REPORT GUARD] [OK] Workspace recovered from disk")
    
    # CRITICAL: Ensure workspace_paths are in tool_context.state for export_executive_report to use
    ws_paths = (state or {}).get("workspace_paths", {}) or {}
    if not ws_paths and tool_context and hasattr(tool_context, 'state'):
        # Try to reconstruct workspace_paths from workspace_root
        workspace_root = state.get("workspace_root")
        if workspace_root and Path(workspace_root).exists():
            ws_paths = {
                "uploads": str(Path(workspace_root) / "uploads"),
                "data": str(Path(workspace_root) / "data"),
                "plots": str(Path(workspace_root) / "plots"),
                "reports": str(Path(workspace_root) / "reports"),
                "results": str(Path(workspace_root) / "results"),
                "models": str(Path(workspace_root) / "models"),
            }
            # Ensure reports and results directories exist
            Path(ws_paths["reports"]).mkdir(parents=True, exist_ok=True)
            Path(ws_paths["results"]).mkdir(parents=True, exist_ok=True)
            # Update state with workspace_paths
            if hasattr(tool_context.state, '__setitem__'):
                tool_context.state["workspace_paths"] = ws_paths
            else:
                state["workspace_paths"] = ws_paths
            logger.info(f"[EXEC REPORT GUARD] Reconstructed workspace_paths: {ws_paths}")
    
    reports_dir = ws_paths.get("reports")
    logger.info(f"[EXEC REPORT GUARD] Reports directory: {reports_dir}")
    logger.info(f"[EXEC REPORT GUARD] Reports dir exists: {Path(reports_dir).exists() if reports_dir else False}")

    # CRITICAL FIX: Since we're in an async function, call the async export_executive_report directly
    # instead of going through the sync wrapper (which causes coroutine reuse issues)
    logger.info(f"[EXEC REPORT GUARD] Calling export_executive_report directly (async)")
    try:
        from .ds_tools import export_executive_report
        # Extract title from kwargs
        title = kwargs.get("title", kwargs.get("project_title", "Data Science Report"))
        csv_path = kwargs.get("csv_path", "")
        
        # Call the async function directly since we're already in async context
        result = await export_executive_report(
            project_title=title,
            csv_path=csv_path,
            tool_context=tool_context
        )
        logger.info(f"[EXEC REPORT GUARD] Underlying tool returned: {type(result)}")
        logger.info(f"[EXEC REPORT GUARD] Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        logger.info(f"[EXEC REPORT GUARD] Result status: {result.get('status') if isinstance(result, dict) else 'N/A'}")
    except Exception as e:
        logger.error(f"[EXEC REPORT GUARD] [X] Failed to call export tool: {e}", exc_info=True)
        return {
            "status": "failed",
            "message": f"Failed to generate executive report: {e}",
            "error": str(e)
        }
    
    if not isinstance(result, dict):
        logger.warning(f"[EXEC REPORT GUARD] Result is not a dict, wrapping it")
        result = {}

    pdf_path = None

    # Honor explicit path if returned
    explicit = result.get("pdf_path") or result.get("path") or result.get("file")
    logger.info(f"[EXEC REPORT GUARD] Explicit path from result: {explicit}")
    if explicit and Path(str(explicit)).suffix.lower() == ".pdf" and _exists(str(explicit)):
        pdf_path = str(explicit)
        logger.info(f"[EXEC REPORT GUARD] Using explicit PDF path: {pdf_path}")
    elif explicit:
        logger.warning(f"[EXEC REPORT GUARD] Explicit path exists but not valid PDF: {explicit}, suffix={Path(str(explicit)).suffix.lower() if explicit else 'N/A'}, exists={_exists(str(explicit)) if explicit else False}")

    # Otherwise pick newest report in reports/
    if not pdf_path and reports_dir and Path(reports_dir).exists():
        logger.info(f"[EXEC REPORT GUARD] Searching for PDFs in {reports_dir}")
        pdfs = list(Path(reports_dir).glob("*.pdf"))
        logger.info(f"[EXEC REPORT GUARD] Found {len(pdfs)} PDF files: {[p.name for p in pdfs]}")
        if pdfs:
            pdfs_sorted = sorted(pdfs, key=lambda p: p.stat().st_mtime, reverse=True)
            pdf_path = str(pdfs_sorted[0])
            logger.info(f"[EXEC REPORT GUARD] Selected newest PDF: {pdf_path}")
    else:
        logger.warning(f"[EXEC REPORT GUARD] Cannot search for PDFs: reports_dir={reports_dir}, exists={Path(reports_dir).exists() if reports_dir else False}")

    if not pdf_path or not _exists(pdf_path):
        logger.error(f"[EXEC REPORT GUARD] [X] NO PDF FOUND! pdf_path={pdf_path}, exists={_exists(pdf_path) if pdf_path else False}")
        # State might be State object or dict, handle both for debugging
        try:
            if hasattr(state, 'items'):
                state_dump = json.dumps({k: str(v)[:100] for k, v in state.items()}, indent=2, default=str)
            else:
                state_dump = f"State type: {type(state)}, attrs: {dir(state)}"
            logger.error(f"[EXEC REPORT GUARD] State dump: {state_dump}")
        except Exception as e:
            logger.error(f"[EXEC REPORT GUARD] Could not dump state: {e}")
        return {
            "status": "failed",
            "message": f"Executive report did not produce a PDF. Reports dir: {reports_dir}, PDF path: {pdf_path}",
            "debug": {
                "reports_dir": reports_dir,
                "pdf_path": pdf_path,
                "result": result,
                "workspace_paths": ws_paths,
            }
        }

    logger.info(f"[EXEC REPORT GUARD] [OK] PDF found: {pdf_path}, size: {Path(pdf_path).stat().st_size} bytes")

    # Register locally and mirror to ADK
    try:
        logger.info(f"[EXEC REPORT GUARD] Registering artifact locally: {pdf_path}")
        artifact_manager.register_artifact(state, pdf_path, kind="report", label=Path(pdf_path).stem)
        artifact_manager.register_and_sync_artifact(tool_context, pdf_path, kind="report", label=Path(pdf_path).stem)
        logger.info(f"[EXEC REPORT GUARD] [OK] Artifact registered and synced")
    except Exception as e:
        logger.error(f"[EXEC REPORT GUARD] [X] Failed to register/sync artifact: {e}", exc_info=True)

    # Save to ADK ArtifactService (user-scoped for long-lived reports)
    artifact_info = None
    if tool_context and hasattr(tool_context, "save_artifact"):
        try:
            logger.info(f"[EXEC REPORT GUARD] Saving to ADK ArtifactService: {pdf_path}")
            artifact_info = await save_path_as_artifact(
                tool_context,
                pdf_path,
                filename=Path(pdf_path).name,
                user_scope=True  # [OK] user-scoped so it persists across sessions
            )
            logger.info(f"[EXEC REPORT GUARD] [OK] Saved to ArtifactService: {artifact_info['filename']} v{artifact_info['version']}")
        except Exception as e:
            logger.error(f"[EXEC REPORT GUARD] [X] Failed to save to ArtifactService: {e}", exc_info=True)
    else:
        logger.warning(f"[EXEC REPORT GUARD] No save_artifact method on context")

    # Friendly UI text with enhanced formatting
    if artifact_info:
        formatted_message = (
            f"📄 **Executive Report Generated:**\n\n"
            f"**{artifact_info['filename']}** (v{artifact_info['version']})\n\n"
            f"✅ **Status:** Saved to Artifacts panel — ready to download!\n"
            f"📊 **Content:** AI-powered executive summary with 6 sections:\n"
            f"  • Executive Summary\n"
            f"  • Key Findings\n"
            f"  • Recommendations\n"
            f"  • Visualizations\n"
            f"  • Methodology\n"
            f"  • Conclusion\n\n"
            f"💡 **View:** Check the Artifacts panel (right side) to download the PDF!"
        )
    else:
        formatted_message = (
            f"📄 **Executive Report Generated:**\n\n"
            f"**{Path(pdf_path).name}**\n\n"
            f"⚠️ **Warning:** Saved locally at: `{pdf_path}`\n"
            f"💡 Check your file system for the report."
        )
    
    logger.info(f"[EXEC REPORT GUARD] Returning success with UI message")
    logger.info(f"[EXEC REPORT GUARD] Display message: {formatted_message[:200]}")
    logger.info("=" * 80)
    
    # [OK] CRITICAL: Add __display__ field for LLM to extract and show in chat
    return {
        "status": "success",
        "__display__": formatted_message,  # HIGHEST PRIORITY display field
        "text": formatted_message,
        "message": formatted_message,
        "ui_text": formatted_message,
        "content": formatted_message,
        "display": formatted_message,
        "_formatted_output": formatted_message,
        "pdf_path": pdf_path,
        "artifact": artifact_info,  # ADK artifact metadata
    }
