"""
Artifact utilities for pushing files to the UI artifacts panel.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# --- MIME helper -------------------------------------------------------------
def guess_mime(path: str) -> str:
    ext = Path(path).suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".pdf": "application/pdf",
        ".csv": "text/csv",
        ".parquet": "application/octet-stream",
        ".json": "application/json",
        ".txt": "text/plain",
    }.get(ext, "application/octet-stream")
    logger.debug(f"[ARTIFACT_UTILS] guess_mime({path}) → {mime}")
    return mime

# --- existence helper --------------------------------------------------------
def _exists(p: str | None) -> bool:
    try:
        exists = bool(p) and Path(p).exists()
        logger.debug(f"[ARTIFACT_UTILS] _exists({p}) → {exists}")
        return exists
    except Exception as e:
        logger.debug(f"[ARTIFACT_UTILS] _exists({p}) raised {e}")
        return False

# --- duplicate debounce ------------------------------------------------------
_uploaded_once: set[tuple[str, int, int]] = set()

async def push_artifact_to_ui(callback_context, abs_path: str, display_name: str | None = None) -> bool:
    """
    Upload a local file to the conversation's Artifacts pane with correct MIME.
    Debounces duplicates within a run.
    """
    from google.genai import types as gen_types
    
    logger.info(f"[ARTIFACT_UTILS] push_artifact_to_ui called: {abs_path}, display_name={display_name}")
    
    try:
        p = Path(abs_path)
        if not p.exists():
            logger.warning(f"[ARTIFACT_UTILS] [X] File does not exist: {abs_path}")
            return False

        logger.info(f"[ARTIFACT_UTILS] File exists: {abs_path}, size={p.stat().st_size} bytes")

        ui_name = (display_name or p.name)
        key = (ui_name, p.stat().st_size, int(p.stat().st_mtime))
        if key in _uploaded_once:
            logger.info(f"[ARTIFACT_UTILS] ⏭  Skipping duplicate upload: {ui_name}")
            return True

        logger.info(f"[ARTIFACT_UTILS] Reading file bytes: {abs_path}")
        data = p.read_bytes()
        logger.info(f"[ARTIFACT_UTILS] Read {len(data)} bytes")
        
        mime = guess_mime(str(p))
        logger.info(f"[ARTIFACT_UTILS] Creating Part with MIME type: {mime}")
        part = gen_types.Part.from_bytes(data=data, mime_type=mime)
        
        logger.info(f"[ARTIFACT_UTILS] Calling callback_context.save_artifact('{ui_name}', Part)")
        await callback_context.save_artifact(ui_name, part)
        logger.info(f"[ARTIFACT_UTILS] [OK] Successfully saved artifact: {ui_name}")
        
        _uploaded_once.add(key)
        return True
    except Exception as e:
        logger.error(f"[ARTIFACT_UTILS] [X] Failed to push artifact {abs_path}: {e}", exc_info=True)
        return False

# --- sync wrapper (safe in async/sync tools) ---------------------------------
def sync_push_artifact(callback_context, abs_path: str, display_name: str | None = None) -> None:
    import asyncio
    from pathlib import Path
    
    logger.info(f"[ARTIFACT_UTILS] sync_push_artifact called: {abs_path}")
    
    try:
        coro = push_artifact_to_ui(callback_context, abs_path, display_name or Path(abs_path).name)
        try:
            loop = asyncio.get_running_loop()
            logger.info(f"[ARTIFACT_UTILS] Using existing event loop to create task")
            loop.create_task(coro)
        except RuntimeError:
            logger.info(f"[ARTIFACT_UTILS] No event loop, using asyncio.run")
            asyncio.run(coro)
    except Exception as e:
        logger.error(f"[ARTIFACT_UTILS] [X] sync_push_artifact failed: {e}", exc_info=True)


# --- Artifact Saving (ADK Native Pattern) ------------------------------------------
async def save_artifact_async(context, filename: str, data: bytes, mime_type: str = "application/octet-stream") -> int | None:
    """
    Save an artifact using ADK's context.save_artifact() pattern (async version).
    
    Based on ADK documentation: context.save_artifact(filename, Part) returns version number.
    
    Args:
        context: Tool context with save_artifact method
        filename: Name for the artifact
        data: Binary data to save
        mime_type: MIME type (default: application/octet-stream)
    
    Returns:
        Version number (starting from 0) or None if failed
    
    Example:
        version = await save_artifact_async(context, "model.joblib", model_bytes, "application/octet-stream")
    """
    try:
        from google.genai.types import Part, Blob
        
        if not context or not hasattr(context, 'save_artifact'):
            logger.warning(f"[ARTIFACT_UTILS] Context does not support save_artifact")
            return None
        
        logger.info(f"[ARTIFACT_UTILS] Saving artifact: {filename}, Size: {len(data)} bytes, MIME: {mime_type}")
        
        # Create Part with inline_data
        artifact_part = Part(inline_data=Blob(mime_type=mime_type, data=data))
        
        # Save artifact (returns version number)
        version = await context.save_artifact(filename=filename, artifact=artifact_part)
        
        logger.info(f"[ARTIFACT_UTILS] ✅ Saved artifact: {filename}, Version: {version}")
        
        return version
        
    except Exception as e:
        logger.error(f"[ARTIFACT_UTILS] Failed to save artifact {filename}: {e}", exc_info=True)
        return None


def save_artifact_sync(context, filename: str, data: bytes, mime_type: str = "application/octet-stream") -> int | None:
    """
    Synchronous wrapper for save_artifact_async.
    
    Args:
        context: Tool context with save_artifact method
        filename: Name for the artifact
        data: Binary data to save
        mime_type: MIME type
    
    Returns:
        Version number or None if failed
    """
    import asyncio
    
    try:
        loop = asyncio.get_running_loop()
        logger.warning(f"[ARTIFACT_UTILS] Cannot await in running loop - use save_artifact_async instead")
        # Create task but can't wait for it
        loop.create_task(save_artifact_async(context, filename, data, mime_type))
        return 0  # Return placeholder version
    except RuntimeError:
        return asyncio.run(save_artifact_async(context, filename, data, mime_type))


# --- Artifact Loading (ADK Native Pattern) ------------------------------------------
async def load_artifact_data_async(context, artifact_name: str) -> tuple[bytes | None, str | None]:
    """
    Load an artifact using ADK's context.load_artifact() pattern (async version).
    
    Based on ADK documentation: context.load_artifact() returns a google.genai.types.Part
    object with inline_data containing data bytes and mime_type.
    
    Args:
        context: Tool context with load_artifact method
        artifact_name: Name of the artifact to load
    
    Returns:
        Tuple of (data bytes, mime_type) or (None, None) if not found
    
    Example:
        data, mime_type = await load_artifact_data_async(context, "model.joblib")
        if data:
            model = joblib.loads(data)
    """
    try:
        if not context or not hasattr(context, 'load_artifact'):
            logger.warning(f"[ARTIFACT_UTILS] Context does not support load_artifact")
            return None, None
        
        logger.info(f"[ARTIFACT_UTILS] Loading artifact: {artifact_name}")
        
        # Load artifact (returns google.genai.types.Part object)
        artifact = await context.load_artifact(filename=artifact_name)
        
        if not artifact:
            logger.warning(f"[ARTIFACT_UTILS] Artifact not found: {artifact_name}")
            return None, None
        
        # Check for text content first (Part.text)
        if hasattr(artifact, 'text') and artifact.text:
            logger.info(f"[ARTIFACT_UTILS] ✅ Loaded text artifact: {artifact_name}")
            return artifact.text.encode('utf-8'), 'text/plain'
        
        # Access inline_data for binary content
        if not hasattr(artifact, 'inline_data') or not artifact.inline_data:
            logger.warning(f"[ARTIFACT_UTILS] Artifact has no inline_data or text: {artifact_name}")
            return None, None
        
        data = artifact.inline_data.data
        mime_type = artifact.inline_data.mime_type
        
        logger.info(f"[ARTIFACT_UTILS] ✅ Loaded artifact: {artifact_name}, MIME: {mime_type}, Size: {len(data)} bytes")
        
        return data, mime_type
        
    except Exception as e:
        logger.error(f"[ARTIFACT_UTILS] Failed to load artifact {artifact_name}: {e}", exc_info=True)
        return None, None


def load_artifact_data(context, artifact_name: str) -> tuple[bytes | None, str | None]:
    """
    Synchronous wrapper for load_artifact_data_async.
    
    Args:
        context: Tool context with load_artifact method
        artifact_name: Name of the artifact to load
    
    Returns:
        Tuple of (data bytes, mime_type) or (None, None) if not found
    """
    import asyncio
    
    try:
        # Try to run async
        loop = asyncio.get_running_loop()
        # If we're in an event loop, create a task
        task = loop.create_task(load_artifact_data_async(context, artifact_name))
        # We can't await it here, so return immediately
        logger.warning(f"[ARTIFACT_UTILS] Cannot await in running loop - use load_artifact_data_async instead")
        return None, None
    except RuntimeError:
        # No event loop - create one and run
        return asyncio.run(load_artifact_data_async(context, artifact_name))


def load_model_artifact(context, model_name: str):
    """
    Load a trained model from artifacts using ADK pattern.
    
    Args:
        context: Tool context
        model_name: Name of the model artifact (e.g., "classifier.joblib")
    
    Returns:
        Loaded model object or None
    
    Example:
        model = load_model_artifact(context, "my_classifier.joblib")
        if model:
            predictions = model.predict(X_test)
    """
    try:
        import joblib
        import io
        
        # Try with .joblib extension if not present
        if not model_name.endswith(('.joblib', '.pkl', '.pickle')):
            model_name = f"{model_name}.joblib"
        
        data, mime_type = load_artifact_data(context, model_name)
        
        if not data:
            logger.warning(f"[ARTIFACT_UTILS] Could not load model artifact: {model_name}")
            return None
        
        # Deserialize model from bytes
        model = joblib.load(io.BytesIO(data))
        logger.info(f"[ARTIFACT_UTILS] ✅ Deserialized model: {model_name}")
        
        return model
        
    except Exception as e:
        logger.error(f"[ARTIFACT_UTILS] Failed to deserialize model {model_name}: {e}", exc_info=True)
        return None


def load_text_artifact(context, artifact_name: str, encoding: str = 'utf-8') -> str | None:
    """
    Load a text artifact (markdown, txt, csv, etc.).
    
    Args:
        context: Tool context
        artifact_name: Name of the text artifact
        encoding: Text encoding (default: utf-8)
    
    Returns:
        Text content or None
    
    Example:
        report = load_text_artifact(context, "analysis_report.md")
        if report:
            print(report)
    """
    try:
        data, mime_type = load_artifact_data(context, artifact_name)
        
        if not data:
            return None
        
        # Decode text
        text = data.decode(encoding)
        logger.info(f"[ARTIFACT_UTILS] ✅ Loaded text artifact: {artifact_name}, Length: {len(text)} chars")
        
        return text
        
    except Exception as e:
        logger.error(f"[ARTIFACT_UTILS] Failed to load text artifact {artifact_name}: {e}", exc_info=True)
        return None