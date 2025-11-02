"""
ADK-native artifact management utilities.
Save files to ADK's ArtifactService for proper UI integration.
"""
import logging
import mimetypes
from pathlib import Path
from google.genai import types

logger = logging.getLogger(__name__)


async def save_path_as_artifact(
    context,
    path: str,
    filename: str | None = None,
    user_scope: bool = False
) -> dict:
    """
    Reads a file from disk and saves it as an ADK Artifact.
    
    Args:
        context: ADK callback context with save_artifact method
        path: File path to save
        filename: Optional custom filename (defaults to basename)
        user_scope: If True, prefix with 'user:' to share across sessions
    
    Returns:
        {"filename": <name>, "version": <int>}
    
    Raises:
        ValueError: If ArtifactService is not configured
    """
    if not hasattr(context, "save_artifact"):
        raise ValueError("ArtifactService is not configured on this context.")

    fname = filename or Path(path).name
    if user_scope and not fname.startswith("user:"):
        fname = f"user:{fname}"

    # Guess MIME type from the actual file extension, not the logical name.
    # Using fname can fail if prefixed (e.g., 'user:plot.png' looks like a URL scheme).
    mime, _ = mimetypes.guess_type(Path(path).name)
    if not mime:
        # Fallback: try stripping any prefix like 'user:' then re-guess
        try:
            logical = fname.split(":", 1)[-1] if ":" in fname else fname
            mime, _ = mimetypes.guess_type(logical)
        except Exception:
            mime = None
    mime = mime or "application/octet-stream"

    logger.info(f"[ARTIFACT IO] Saving {path} as artifact '{fname}' (mime: {mime})")

    try:
        with open(path, "rb") as f:
            data = f.read()

        part = types.Part(inline_data=types.Blob(mime_type=mime, data=data))
        version = await context.save_artifact(filename=fname, artifact=part)
        
        logger.info(f"[ARTIFACT IO] [OK] Saved artifact '{fname}' version {version}")
        return {"filename": fname, "version": version}
    except Exception as e:
        logger.error(f"[ARTIFACT IO] [X] Failed to save artifact: {e}", exc_info=True)
        raise


async def save_figure_as_artifact(
    context,
    fig,
    filename: str = "plot.png",
    user_scope: bool = False
) -> dict:
    """
    Saves a matplotlib figure directly as an artifact (no temp file needed).
    
    Args:
        context: ADK callback context
        fig: matplotlib Figure object
        filename: Name for the artifact
        user_scope: If True, prefix with 'user:'
    
    Returns:
        {"filename": <name>, "version": <int>}
    """
    import io
    
    if not hasattr(context, "save_artifact"):
        raise ValueError("ArtifactService is not configured on this context.")

    if user_scope and not filename.startswith("user:"):
        filename = f"user:{filename}"

    logger.info(f"[ARTIFACT IO] Saving matplotlib figure as artifact '{filename}'")

    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        buf.seek(0)
        
        part = types.Part(inline_data=types.Blob(mime_type="image/png", data=buf.read()))
        version = await context.save_artifact(filename=filename, artifact=part)
        
        logger.info(f"[ARTIFACT IO] [OK] Saved figure artifact '{filename}' version {version}")
        return {"filename": filename, "version": version}
    except Exception as e:
        logger.error(f"[ARTIFACT IO] [X] Failed to save figure: {e}", exc_info=True)
        raise


def announce_artifact(name: str, version: int, note: str = "") -> dict:
    """
    Returns a consistent artifact announcement for tool responses.
    
    Args:
        name: Artifact filename
        version: Artifact version number
        note: Optional additional note
    
    Returns:
        Tool response dict with status, artifact info, and UI message
    """
    message = f"[OK] Saved artifact: **{name}** (v{version})"
    if note:
        message += f"\n{note}"
    
    return {
        "status": "success",
        "artifact": {"filename": name, "version": version},
        "message": message,
        "ui_text": message,
    }

