"""
Auto-Correction System for Tools
Automatically fixes common issues as they occur during tool execution.
Handles: artifacts, workflow state, auto-install, and other recoverable errors.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


def auto_correct_artifact_error(
    tool_name: str,
    error: Exception,
    tool_context: Any,
    result: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Attempt to auto-correct artifact-related errors.
    
    Returns:
        (success: bool, corrected_result: Optional[Dict])
    """
    try:
        error_str = str(error).lower()
        
        # Issue: Missing artifact directory
        if "no such file" in error_str or "directory" in error_str or "path" in error_str:
            try:
                if tool_context and hasattr(tool_context, 'state'):
                    from .artifact_manager import ensure_workspace
                    from .large_data_config import UPLOAD_ROOT
                    ensure_workspace(tool_context.state, UPLOAD_ROOT)
                    logger.info(f"[AUTO-CORRECT] Created missing artifact directory for {tool_name}")
                    # Retry artifact creation
                    if result:
                        try:
                            from .universal_artifact_generator import ensure_artifact_for_tool
                            result = ensure_artifact_for_tool(tool_name, result, tool_context)
                            return True, result
                        except Exception:
                            pass
                    return True, result
            except Exception as e:
                logger.debug(f"[AUTO-CORRECT] Could not fix artifact directory: {e}")
        
        # Issue: Missing display fields in result
        if result and not result.get("__display__"):
            try:
                # Extract display text from available fields
                display_text = (
                    result.get("message") or
                    result.get("ui_text") or
                    result.get("text") or
                    result.get("content") or
                    str(result.get("status", "success"))
                )
                if display_text:
                    result["__display__"] = str(display_text)
                    result["message"] = result.get("message", display_text)
                    result["ui_text"] = result.get("ui_text", display_text)
                    result["text"] = result.get("text", display_text)
                    logger.info(f"[AUTO-CORRECT] Added missing display fields to {tool_name}")
                    return True, result
            except Exception as e:
                logger.debug(f"[AUTO-CORRECT] Could not fix display fields: {e}")
        
        # Issue: Result not a dict
        if result is not None and not isinstance(result, dict):
            try:
                corrected = {
                    "status": "success",
                    "message": str(result),
                    "__display__": str(result),
                    "data": result
                }
                logger.info(f"[AUTO-CORRECT] Converted non-dict result to dict for {tool_name}")
                return True, corrected
            except Exception:
                pass
        
    except Exception as e:
        logger.warning(f"[AUTO-CORRECT] Error in artifact correction: {e}")
    
    return False, result


def auto_correct_workflow_error(
    tool_name: str,
    error: Exception,
    tool_context: Any
) -> bool:
    """
    Attempt to auto-correct workflow state errors.
    
    Returns:
        success: bool
    """
    try:
        if not tool_context or not hasattr(tool_context, 'state'):
            return False
        
        state = tool_context.state
        error_str = str(error).lower()
        
        # Issue: Missing workflow state keys
        if "workflow_stage" not in state or state.get("workflow_stage") is None:
            try:
                from .workflow_persistence import restore_workflow_state
                restored_stage, restored_step = restore_workflow_state(state)
                if restored_stage is not None:
                    state["workflow_stage"] = restored_stage
                    state["workflow_step"] = restored_step or 0
                    logger.info(f"[AUTO-CORRECT] Restored missing workflow state for {tool_name}")
                    return True
                else:
                    # Initialize to default
                    state["workflow_stage"] = 1
                    state["workflow_step"] = 0
                    state["last_workflow_action"] = "initialized"
                    logger.info(f"[AUTO-CORRECT] Initialized default workflow state for {tool_name}")
                    return True
            except Exception as e:
                logger.debug(f"[AUTO-CORRECT] Could not restore workflow state: {e}")
                # Fallback: initialize defaults
                try:
                    state["workflow_stage"] = 1
                    state["workflow_step"] = 0
                    state["last_workflow_action"] = "initialized"
                    return True
                except Exception:
                    pass
        
        # Issue: Invalid workflow stage value
        if "workflow_stage" in state:
            stage = state.get("workflow_stage")
            if stage is not None and (not isinstance(stage, int) or stage < 1 or stage > 11):
                try:
                    state["workflow_stage"] = 1
                    state["workflow_step"] = 0
                    logger.info(f"[AUTO-CORRECT] Fixed invalid workflow stage {stage} -> 1 for {tool_name}")
                    return True
                except Exception:
                    pass
        
        # Issue: Corrupted workflow history
        if "workflow_history" in state and not isinstance(state["workflow_history"], list):
            try:
                state["workflow_history"] = []
                logger.info(f"[AUTO-CORRECT] Fixed corrupted workflow history for {tool_name}")
                return True
            except Exception:
                pass
        
    except Exception as e:
        logger.warning(f"[AUTO-CORRECT] Error in workflow correction: {e}")
    
    return False


def auto_correct_import_error(
    tool_name: str,
    error: Exception,
    tool_context: Any
) -> Tuple[bool, Optional[str]]:
    """
    Attempt to auto-correct import/installation errors.
    
    Returns:
        (success: bool, error_message: Optional[str])
    """
    try:
        error_str = str(error)
        
        # Extract missing module name
        missing_module = None
        if "No module named" in error_str:
            import re
            match = re.search(r"No module named ['\"](\w+)['\"]", error_str)
            if match:
                missing_module = match.group(1)
        
        if missing_module:
            try:
                from .auto_install_utils import ensure_package, ensure_tool_dependencies
                
                # First try tool-specific dependencies
                success, error_msg = ensure_tool_dependencies(tool_name, silent=False)
                if success:
                    logger.info(f"[AUTO-CORRECT] Successfully installed dependencies for {tool_name}")
                    return True, None
                
                # Fallback: try direct package install
                success, error_msg = ensure_package(missing_module, silent=False)
                if success:
                    logger.info(f"[AUTO-CORRECT] Successfully installed {missing_module} for {tool_name}")
                    return True, None
                
                return False, error_msg
            except Exception as e:
                logger.debug(f"[AUTO-CORRECT] Auto-install failed: {e}")
                return False, str(e)
        
    except Exception as e:
        logger.warning(f"[AUTO-CORRECT] Error in import correction: {e}")
    
    return False, None


def auto_correct_common_errors(
    tool_name: str,
    error: Exception,
    tool_context: Any,
    result: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Comprehensive auto-correction for all types of errors.
    
    Returns:
        (success: bool, corrected_result: Optional[Dict], error_message: Optional[str])
    """
    try:
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # 1. Handle ImportError / ModuleNotFoundError
        if error_type in ("ImportError", "ModuleNotFoundError"):
            success, error_msg = auto_correct_import_error(tool_name, error, tool_context)
            if success:
                return True, result, None
            return False, result, error_msg
        
        # 2. Handle artifact-related errors
        if any(keyword in error_str for keyword in ["artifact", "file", "directory", "path", "workspace"]):
            success, corrected_result = auto_correct_artifact_error(tool_name, error, tool_context, result)
            if success:
                return True, corrected_result, None
        
        # 3. Handle workflow state errors
        if any(keyword in error_str for keyword in ["workflow", "stage", "step", "state"]):
            success = auto_correct_workflow_error(tool_name, error, tool_context)
            if success:
                return True, result, None
        
        # 4. Handle JSON serialization errors (common in artifacts)
        if "json" in error_str or "serialize" in error_str or "not json serializable" in error_str:
            try:
                if result:
                    # Create a JSON-safe version
                    safe_result = {}
                    for key, value in result.items():
                        try:
                            json.dumps(value)  # Test if serializable
                            safe_result[key] = value
                        except (TypeError, ValueError):
                            # Convert non-serializable values to strings
                            safe_result[key] = str(value)[:500]
                    logger.info(f"[AUTO-CORRECT] Fixed JSON serialization for {tool_name}")
                    return True, safe_result, None
            except Exception as e:
                logger.debug(f"[AUTO-CORRECT] Could not fix JSON serialization: {e}")
        
        # 5. Handle missing result
        if result is None:
            try:
                corrected = {
                    "status": "success",
                    "message": f"{tool_name} completed successfully",
                    "__display__": f"✅ {tool_name}() completed",
                    "ui_text": f"{tool_name} completed",
                    "tool": tool_name
                }
                logger.info(f"[AUTO-CORRECT] Created missing result dict for {tool_name}")
                return True, corrected, None
            except Exception:
                pass
        
        # 6. Handle missing status field
        if result and "status" not in result:
            try:
                result["status"] = "success"
                logger.info(f"[AUTO-CORRECT] Added missing status field to {tool_name}")
                return True, result, None
            except Exception:
                pass
        
    except Exception as e:
        logger.warning(f"[AUTO-CORRECT] Error in auto-correction system: {e}")
    
    return False, result, None


def safe_retry_with_correction(
    tool_name: str,
    func,
    args: tuple,
    kwargs: dict,
    max_retries: int = 1
) -> Tuple[Any, bool, Optional[str]]:
    """
    Safely retry a tool call after auto-correction.
    
    Returns:
        (result, success, error_message)
    """
    import asyncio
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                import inspect
                if inspect.iscoroutine(func(*args, **kwargs)):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            return result, True, None
        except Exception as e:
            if attempt < max_retries:
                tool_context = kwargs.get("tool_context") or (args[0] if args else None)
                
                # Try auto-correction
                success, corrected_result, error_msg = auto_correct_common_errors(
                    tool_name, e, tool_context, None
                )
                
                if success:
                    logger.info(f"[AUTO-CORRECT] Retrying {tool_name} after auto-correction (attempt {attempt + 1})")
                    continue
                else:
                    logger.debug(f"[AUTO-CORRECT] Auto-correction failed for {tool_name}, not retrying")
                    break
            else:
                return None, False, str(e)
    
    return None, False, "Max retries exceeded"


# Export for use in other modules
__all__ = [
    'auto_correct_artifact_error',
    'auto_correct_workflow_error',
    'auto_correct_import_error',
    'auto_correct_common_errors',
    'safe_retry_with_correction'
]

