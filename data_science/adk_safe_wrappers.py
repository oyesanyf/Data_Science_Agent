"""
ADK-safe wrappers for all tools that use ToolContext or CallbackContext.
These wrappers expose only JSON-serializable parameters to ADK's schema generator.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from .utils_state import get_context_info, set_temp, get_temp
from .utils_tools import assert_json_signature
import asyncio
import nest_asyncio
import logging
import math
import decimal
import numpy as np
import os

# Apply nest_asyncio globally to handle nested event loops
nest_asyncio.apply()

logger = logging.getLogger(__name__)

def _log_tool_result_diagnostics(result: Any, tool_name: str, stage: str = "output"):
    """
    Universal diagnostic logger for tool results.
    Logs detailed information about what data a tool is returning.
    
    Args:
        result: The tool result to diagnose
        tool_name: Name of the tool
        stage: Stage in processing (e.g., "output", "after_wrapper", "pre_display")
    """
    try:
        result_type = type(result).__name__
        
        # Log diagnostics at DEBUG level to reduce console spam
        logger.debug(f"[TOOL DIAGNOSTIC] {tool_name} - {stage}: type={result_type}")
        
        if isinstance(result, dict):
            keys = list(result.keys())
            logger.debug(f"[TOOL DIAGNOSTIC] Dict keys ({len(keys)}): {keys}")
            
            # Log critical fields (summary only, not full content)
            for key in ['status', 'message', 'error', 'ui_text', '__display__', 'overview', 'shape', 'columns', 'artifacts']:
                if key in result:
                    value = result[key]
                    if value is None:
                        value_str = "None"
                    elif isinstance(value, str):
                        value_str = f"str[{len(value)} chars]"
                    elif isinstance(value, (int, float, bool)):
                        value_str = str(value)
                    elif isinstance(value, (list, tuple)):
                        value_str = f"{type(value).__name__}[{len(value)}]"
                    elif isinstance(value, dict):
                        value_str = f"dict[{len(value)} keys]"
                    else:
                        value_str = f"{type(value).__name__}"
                    
                    logger.debug(f"[TOOL DIAGNOSTIC]   {key}: {value_str}")
        else:
            value_length = len(str(result)) if result else 0
            logger.debug(f"[TOOL DIAGNOSTIC] Value length: {value_length} chars")
        
    except Exception as e:
        logger.error(f"[TOOL DIAGNOSTIC] Failed to log diagnostics for {tool_name}: {e}")

def _run_async(coro):
    """
    Helper to run async functions from sync context.
    
    Fixed to handle running event loops correctly - cannot use run_until_complete
    or asyncio.run when loop is already running.
    """
    import concurrent.futures
    
    try:
        # Check if there's an event loop
        loop = asyncio.get_event_loop()
        
        # CRITICAL FIX: Cannot use run_until_complete when loop is running
        # This causes "RuntimeError: This event loop is already running"
        if loop.is_running():
            # Run in executor (separate thread with its own event loop)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            # Loop exists but not running - safe to use run_until_complete
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop - create one and use asyncio.run
        return asyncio.run(coro)

def _ensure_artifacts_created(result: Dict[str, Any], tool_name: str, tool_context: Any) -> Dict[str, Any]:
    """
    LLM-Enforced Artifact Creation - ensures ALL artifacts are:
    1. Created and saved to UI (via ADK artifact service)
    2. Saved as MD files with results
    3. Saved to filesystem
    
    Uses LLM to:
    - Determine required artifacts based on tool result
    - Validate that all artifacts were created correctly
    - Enforce compliance with ADK best practices
    
    Based on ADK documentation patterns for artifact management.
    """
    # Tools logger setup (not currently used but kept for future use)
    tools_logger = logger
    try:
        from .logging_config import get_tools_logger
        tools_logger = get_tools_logger()
    except ImportError:
        pass
    
    try:
        logger.info(f"[ARTIFACT] Ensuring artifacts created for tool '{tool_name}'")
        
        # Use LLM-enforced artifact creation
        from .llm_artifact_enforcer import llm_enforce_artifact_creation
        
        # Check if LLM enforcement is enabled (default: enabled)
        use_llm_enforcement = os.getenv("USE_LLM_ARTIFACT_ENFORCEMENT", "1").lower() in ("1", "true", "yes")
        
        if use_llm_enforcement:
            logger.debug(f"[ARTIFACT] Using LLM-enforced artifact creation for '{tool_name}'")
            result = llm_enforce_artifact_creation(result, tool_name, tool_context)
            logger.info(f"[ARTIFACT] ✅ LLM-enforced artifact creation completed for tool '{tool_name}'")
            logger.info(f"[ARTIFACT] LLM-enforced artifact creation completed for {tool_name}")
        else:
            # Fallback to regular artifact creation
            logger.debug(f"[ARTIFACT] Using standard artifact creation for '{tool_name}'")
            from .universal_artifact_creator import ensure_artifact_creation
            result = ensure_artifact_creation(result, tool_name, tool_context)
            logger.info(f"[ARTIFACT] ✅ Standard artifact creation completed for tool '{tool_name}'")
    except Exception as e:
        logger.error(f"[ARTIFACT] ✗ LLM enforcement failed for '{tool_name}', using fallback: {e}")
        logger.warning(f"[ARTIFACT] LLM enforcement failed, using fallback: {e}")
        # Fallback to regular artifact creation if LLM enforcement fails
        try:
            from .universal_artifact_creator import ensure_artifact_creation
            result = ensure_artifact_creation(result, tool_name, tool_context)
            logger.info(f"[ARTIFACT] ✅ Fallback artifact creation completed for tool '{tool_name}'")
        except Exception as e2:
            logger.error(f"[ARTIFACT] ✗ Fallback artifact creation also failed for '{tool_name}': {e2}")
            logger.debug(f"[ARTIFACT] Fallback also failed: {e2}")
    return result


def _create_tool_artifact(result: Dict[str, Any], tool_name: str, tool_context: Any) -> Dict[str, Any]:
    """
    Universal artifact creator - creates markdown artifacts for ALL tool results.
    
    Pattern adapted from plot_tool: Every tool should save its output as a markdown artifact.
    This ensures results are visible in the UI even if the tool result dict doesn't display properly.
    
    Args:
        result: The tool result dictionary
        tool_name: Name of the tool (used for filename)
        tool_context: Tool context with state/workspace info
    
    Returns:
        Updated result dict with artifact path added
    """
    try:
        from pathlib import Path
        import json
        
        if not tool_context:
            return result
        
        state = getattr(tool_context, "state", {})
        workspace_root = state.get("workspace_root")
        
        if not workspace_root:
            logger.debug(f"[ARTIFACT] No workspace_root for {tool_name}, skipping artifact creation")
            return result
        
        # Skip if result is a failure/error (but log it)
        if result.get("status") == "failed" or result.get("error"):
            logger.debug(f"[ARTIFACT] Skipping artifact for {tool_name} - result has error")
            return result
        
        # Create reports directory
        reports_dir = Path(workspace_root) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Build markdown content from result
        markdown_parts = [f"# {tool_name.replace('_', ' ').title()} Output\n"]
        markdown_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        markdown_parts.append("---\n")
        
        # Add main message/content
        display_text = (result.get("__display__") or 
                       result.get("message") or 
                       result.get("ui_text") or 
                       result.get("content") or
                       result.get("text"))
        
        if display_text:
            markdown_parts.append(f"\n{display_text}\n")
        
        # Add metrics if available
        if "metrics" in result and isinstance(result["metrics"], dict):
            markdown_parts.append("\n## Metrics\n")
            for key, value in result["metrics"].items():
                if not key.startswith("_"):
                    markdown_parts.append(f"- **{key}**: {value}\n")
        
        # Add model info if this is a model-related tool (but don't save binary files)
        if "model_path" in result:
            markdown_parts.append(f"\n## Model\n")
            markdown_parts.append(f"- **Path**: `{result['model_path']}`\n")
            if "model_type" in result:
                markdown_parts.append(f"- **Type**: {result['model_type']}\n")
            if "model_name" in result:
                markdown_parts.append(f"- **Name**: `{result['model_name']}`\n")
                markdown_parts.append(f"\n*Model registered globally - accessible by accuracy, evaluate, predict tools*\n")
        
        # Add shape info
        if "shape" in result:
            markdown_parts.append(f"\n## Data Shape\n")
            if isinstance(result["shape"], (list, tuple)) and len(result["shape"]) == 2:
                markdown_parts.append(f"- **Rows**: {result['shape'][0]:,}\n")
                markdown_parts.append(f"- **Columns**: {result['shape'][1]}\n")
            else:
                markdown_parts.append(f"- **Shape**: {result['shape']}\n")
        
        # Add artifacts list if present (but exclude model files)
        model_extensions = {'.joblib', '.pkl', '.pickle', '.h5', '.pt', '.pth', '.onnx', '.pb', '.safetensors'}
        if "artifacts" in result and result["artifacts"]:
            non_model_artifacts = []
            for art in result["artifacts"]:
                art_str = str(art).lower()
                if not any(art_str.endswith(ext) for ext in model_extensions):
                    non_model_artifacts.append(art)
            
            if non_model_artifacts:
                markdown_parts.append(f"\n## Generated Files\n")
                for art in non_model_artifacts[:20]:  # Limit to 20
                    art_name = str(art).split('/')[-1].split('\\')[-1]
                    markdown_parts.append(f"- `{art_name}`\n")
        
        # Add status
        status = result.get("status", "success")
        markdown_parts.append(f"\n---\n*Status: {status}*\n")
        
        markdown_content = "".join(markdown_parts)
        
        # Save markdown file
        artifact_path = reports_dir / f"{tool_name}_output.md"
        artifact_path.write_text(markdown_content, encoding="utf-8")
        logger.info(f"[ARTIFACT] ✅ Created {artifact_path.name}")
        
        # Push to UI (same as plot does)
        try:
            from .artifact_utils import sync_push_artifact
            sync_push_artifact(tool_context, str(artifact_path), display_name=f"{tool_name}_output.md")
            logger.info(f"[ARTIFACT] ✅ Pushed {tool_name}_output.md to UI")
        except Exception as e:
            logger.warning(f"[ARTIFACT] Could not push to UI: {e}")
        
        # Add to artifacts list
        if "artifacts" not in result:
            result["artifacts"] = []
        if str(artifact_path) not in result["artifacts"]:
            result["artifacts"].append(str(artifact_path))
        
        return result
        
    except Exception as e:
        logger.error(f"[ARTIFACT] Failed to create artifact for {tool_name}: {e}")
        return result


def _register_trained_model(result: Dict[str, Any], tool_context: Any) -> Dict[str, Any]:
    """
    Register a trained model in the global registry.
    MUST be called by ALL model training tools.
    
    Args:
        result: Tool result with model info
        tool_context: Tool context with workspace info
    
    Returns:
        Updated result with registration info
    """
    try:
        from .model_registry import register_model, create_model_md_artifact
        
        if not tool_context:
            return result
        
        state = getattr(tool_context, "state", {})
        workspace_root = state.get("workspace_root")
        
        if not workspace_root:
            return result
        
        # Check if this is a model training result
        model_path = result.get("model_path")
        if not model_path:
            return result  # Not a model training tool
        
        # Extract model info
        model_name = result.get("model_name") or Path(model_path).stem
        model_type = result.get("model_type", "Unknown")
        target = result.get("target", "Unknown")
        metrics = result.get("metrics", {})
        
        # Register model (includes saving to ADK artifact system)
        registry_entry = register_model(
            model_name=model_name,
            model_path=model_path,
            model_type=model_type,
            target=target,
            metrics=metrics,
            metadata=result.get("metadata", {}),
            workspace_root=workspace_root,
            tool_context=tool_context  # Pass context for ADK artifact saving
        )
        
        # Create model-specific MD artifact
        md_path = create_model_md_artifact(registry_entry, workspace_root)
        
        if md_path:
            if "artifacts" not in result:
                result["artifacts"] = []
            if md_path not in result["artifacts"]:
                result["artifacts"].append(md_path)
        
        result["model_registered"] = True
        result["registry_entry"] = registry_entry
        
        logger.info(f"[MODEL REGISTRY] ✅ Registered model: {model_name}")
        
        return result
        
    except Exception as e:
        logger.error(f"[MODEL REGISTRY] Failed to register model: {e}")
        return result

def _to_py_scalar(v):
    """Convert numpy/pandas scalars and handle special float values."""
    if isinstance(v, (np.generic,)):
        return v.item()
    if hasattr(v, 'isoformat'):  # Timestamp, Timedelta, datetime
        try:
            return v.isoformat()
        except:
            return str(v)
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None  # Convert NaN/Inf to None for JSON
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, set):
        return list(v)
    return v

def normalize_nested(obj):
    """
    Recursively normalize nested structures to JSON-safe types.
    Handles numpy, pandas, NaN, Inf, Decimal, sets, timestamps, etc.
    Recommended by ADK best practices for bullet-proof serialization.
    """
    if isinstance(obj, dict):
        return {str(k): normalize_nested(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [normalize_nested(v) for v in obj]
    return _to_py_scalar(obj)

def _resolve_csv_path(csv_path: str, tool_context: Any, tool_name: str = "tool") -> str:
    """
    ✅ UNIVERSAL CSV PATH RESOLVER
    
    Ensures ALL tools use the uploaded file from session state.
    
    Priority:
    1. Explicit csv_path parameter (if provided)
    2. state["default_csv_path"] (from file upload)
    3. Empty string (tool will handle fallback)
    
    Usage:
        csv_path = _resolve_csv_path(csv_path, tool_context, "my_tool")
        # csv_path now points to the uploaded file if available
    """
    from pathlib import Path
    
    # If explicit csv_path provided, use it (user/agent override)
    if csv_path:
        return csv_path
    
    # Try to get uploaded file from state
    if tool_context and hasattr(tool_context, "state"):
        try:
            state = tool_context.state
            default_csv_from_state = state.get("default_csv_path")
            force_default = state.get("force_default_csv", False)
            
            if force_default and default_csv_from_state:
                logger.info(f"[{tool_name.upper()}] Using uploaded file from state: {Path(default_csv_from_state).name}")
                return str(default_csv_from_state)
        except Exception as e:
            logger.warning(f"[{tool_name.upper()}] Could not read uploaded file from state: {e}")
    
    # Return empty string - tool will handle its own fallback logic
    return csv_path

def _ensure_ui_display(result: Any, tool_name: str = "tool", tool_context: Any = None) -> Dict[str, Any]:
    """
    Universal helper to ensure ANY tool result has proper UI display fields.
    
    This is called by ALL tool wrappers to guarantee results appear in the UI.
    
    Args:
        result: The raw result from a tool (can be dict, string, list, None, etc.)
        tool_name: Name of the tool for contextual messaging
        tool_context: Optional tool context for artifact creation
    
    Returns:
        Dict with guaranteed __display__ field and all other display fields
    
    Priority:
        1. If result already has __display__, keep it
        2. Extract from message/text/ui_text fields
        3. Format based on result type (success message, artifacts, data summary)
        4. Fallback to simple success message
    """
    # DIAGNOSTIC: Log what we received
    _log_tool_result_diagnostics(result, tool_name, stage="input_to_ensure_ui_display")
    
    # Convert non-dict results to dict
    if not isinstance(result, dict):
        if result is None:
            result = {"status": "success", "message": f"{tool_name} completed successfully"}
        elif isinstance(result, str):
            result = {"status": "success", "message": result}
        elif isinstance(result, (list, tuple)):
            result = {"status": "success", "data": result, "message": f"{tool_name} returned {len(result)} items"}
        else:
            result = {"status": "success", "data": result, "message": f"{tool_name} completed"}
    
    # If __display__ already exists and is non-empty, ensure other fields match
    if "__display__" in result and result["__display__"]:
        msg = result["__display__"]
        result["text"] = msg
        result["message"] = result.get("message", msg)
        result["ui_text"] = msg
        result["content"] = msg
        result["display"] = msg
        result["_formatted_output"] = msg
        return result
    
    # Extract or build display message
    msg = (result.get("ui_text") or 
           result.get("message") or 
           result.get("text") or 
           result.get("content") or 
           result.get("_formatted_output"))
    
    # If no message found, build one from result contents
    if not msg:
        parts = []
        
        # CRITICAL: Extract actual data from nested 'result' key FIRST
        nested_result = result.get("result")
        if nested_result and isinstance(nested_result, dict):
            # Build detailed message from nested result data
            data_parts = []
            
            # Extract overview information
            if "overview" in nested_result:
                overview = nested_result["overview"]
                if isinstance(overview, dict):
                    if "shape" in overview:
                        shape = overview["shape"]
                        if isinstance(shape, dict):
                            rows = shape.get('rows', 'N/A')
                            cols = shape.get('cols', 'N/A')
                            data_parts.append(f"**Shape:** {rows} rows × {cols} columns")
                    
                    if "columns" in overview:
                        cols = overview["columns"]
                        if isinstance(cols, list):
                            if len(cols) <= 10:
                                data_parts.append(f"**Columns ({len(cols)}):** {', '.join(str(c) for c in cols)}")
                            else:
                                data_parts.append(f"**Columns ({len(cols)}):** {', '.join(str(c) for c in cols[:10])}...")
                    
                    if "memory_usage" in overview:
                        mem = overview["memory_usage"]
                        data_parts.append(f"**Memory:** {mem}")
            
            # Extract numeric summary
            if "numeric_summary" in nested_result:
                num_sum = nested_result["numeric_summary"]
                if isinstance(num_sum, dict) and num_sum:
                    data_parts.append(f"\n**📊 Numeric Features ({len(num_sum)}):**")
                    for col, stats in list(num_sum.items())[:5]:
                        if isinstance(stats, dict):
                            mean_val = stats.get('mean', 0)
                            std_val = stats.get('std', 0)
                            if isinstance(mean_val, (int, float)) and isinstance(std_val, (int, float)):
                                data_parts.append(f"  • **{col}**: mean={mean_val:.2f}, std={std_val:.2f}")
                            else:
                                data_parts.append(f"  • **{col}**: {stats}")
                    if len(num_sum) > 5:
                        data_parts.append(f"  *...and {len(num_sum) - 5} more*")
            
            # Extract categorical summary
            if "categorical_summary" in nested_result:
                cat_sum = nested_result["categorical_summary"]
                if isinstance(cat_sum, dict) and cat_sum:
                    data_parts.append(f"\n**📑 Categorical Features ({len(cat_sum)}):**")
                    for col, info in list(cat_sum.items())[:5]:
                        if isinstance(info, dict):
                            unique_count = info.get('unique_count', 'N/A')
                            top_value = info.get('top_value', 'N/A')
                            data_parts.append(f"  • **{col}**: {unique_count} unique values (most common: {top_value})")
                    if len(cat_sum) > 5:
                        data_parts.append(f"  *...and {len(cat_sum) - 5} more*")
            
            # Extract correlations
            if "correlations" in nested_result:
                corrs = nested_result["correlations"]
                if isinstance(corrs, dict) and "strong" in corrs:
                    strong = corrs["strong"]
                    if isinstance(strong, list) and strong:
                        data_parts.append(f"\n**🔗 Strong Correlations ({len(strong)}):**")
                        for pair in strong[:3]:
                            if isinstance(pair, dict):
                                col1 = pair.get('col1', '?')
                                col2 = pair.get('col2', '?')
                                corr_val = pair.get('correlation', 0)
                                if isinstance(corr_val, (int, float)):
                                    data_parts.append(f"  • {col1} ↔ {col2}: {corr_val:.3f}")
                        if len(strong) > 3:
                            data_parts.append(f"  *...and {len(strong) - 3} more*")
            
            # Extract outliers
            if "outliers" in nested_result:
                outliers = nested_result["outliers"]
                if isinstance(outliers, dict):
                    outlier_cols = [k for k, v in outliers.items() if isinstance(v, dict) and v.get("count", 0) > 0]
                    if outlier_cols:
                        data_parts.append(f"\n**⚠️ Outliers Detected:** {len(outlier_cols)} columns with outliers")
            
            # Extract target information
            if "target" in nested_result:
                target_info = nested_result["target"]
                if isinstance(target_info, dict) and target_info.get("name"):
                    target_name = target_info.get("name")
                    target_type = target_info.get("type", "unknown")
                    data_parts.append(f"\n**🎯 Target Variable:** {target_name} ({target_type})")
            
            # If we successfully extracted data, use it as the message
            if data_parts:
                msg = "📊 **Dataset Analysis Results**\n\n" + "\n".join(data_parts)
                parts.append(msg)
        
        # Add status indicator (only if we haven't already added detailed data)
        if not parts:
            status = result.get("status", "success")
            if status == "success":
                parts.append("✅ **Operation Complete**\n")
            elif status == "failed" or status == "error":
                parts.append("❌ **Operation Failed**\n")
            else:
                parts.append(f"**Status:** {status}\n")
        
        # Check for artifacts - ALL artifacts must be displayed per ADK best practices
        # (except model files which are large binary files)
        artifacts = []
        model_extensions = {'.joblib', '.pkl', '.pickle', '.h5', '.pt', '.pth', '.onnx', '.pb', '.safetensors'}
        
        for key in ["artifacts", "artifact", "saved_files", "files", "output_files", "plot_paths", "figure_paths", "artifact_generated"]:
            val = result.get(key)
            if val:
                if isinstance(val, list):
                    # Ensure all items are strings (serializable)
                    for item in val:
                        if isinstance(item, str):
                            artifacts.append(item)
                        elif hasattr(item, '__str__'):
                            artifacts.append(str(item))
                elif isinstance(val, str):
                    artifacts.append(val)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_artifacts = []
        for artifact in artifacts:
            if artifact not in seen:
                seen.add(artifact)
                unique_artifacts.append(artifact)
        
        # Separate model files from displayable artifacts
        ui_artifacts = []
        model_files = []
        
        for artifact in unique_artifacts:
            artifact_str = str(artifact).lower()
            # Check if it's a model file
            is_model_file = any(artifact_str.endswith(ext) for ext in model_extensions)
            if is_model_file:
                model_files.append(artifact)
            else:
                ui_artifacts.append(artifact)
        
        # Display all non-model artifacts (reports, plots, data files, etc.)
        if ui_artifacts:
            parts.append("**📄 Generated Artifacts (Available for Viewing):**")
            for artifact in ui_artifacts[:30]:  # Increased limit for better visibility
                # Extract just filename for cleaner display
                artifact_name = artifact.split('/')[-1].split('\\')[-1]
                parts.append(f"  • `{artifact_name}`")
            
            if len(ui_artifacts) > 30:
                parts.append(f"  • *...and {len(ui_artifacts) - 30} more*")
            parts.append("")
        
        # Add note about model files (stored but not displayed in UI)
        if model_files:
            parts.append(f"*✓ {len(model_files)} model file(s) saved to workspace (binary files - use load_model to access)*\n")
        
        # Check for metrics/data summary
        metrics = result.get("metrics")
        if metrics and isinstance(metrics, dict):
            parts.append("**Metrics:**")
            for k, v in list(metrics.items())[:10]:  # Limit to 10 metrics
                if not k.startswith("_") and isinstance(v, (int, float, str, bool)):
                    parts.append(f"  • **{k}:** {v}")
            parts.append("")
        
        # Check for model_path or file paths
        if "model_path" in result:
            parts.append(f"**Model saved:** `{result['model_path']}`\n")
        
        if "pdf_path" in result:
            parts.append(f"**Report saved:** `{result['pdf_path']}`\n")
        
        # Fallback message
        if len(parts) == 1:  # Only status line
            parts.append(f"**{tool_name}** completed successfully")
        
        msg = "\n".join(parts)
    
    # Add ALL display fields for maximum compatibility
    result["__display__"] = msg
    result["text"] = msg
    result["message"] = result.get("message", msg)  # Preserve original if exists
    result["ui_text"] = msg
    result["content"] = msg
    result["display"] = msg
    result["_formatted_output"] = msg
    
    # Ensure status exists
    if "status" not in result:
        result["status"] = "success"
    
    # ===== CRITICAL: Ensure artifacts list is properly serialized =====
    # Per ADK documentation: All result fields must be JSON-serializable
    # Artifacts should be a list of strings (filenames/paths)
    if "artifacts" in result:
        if isinstance(result["artifacts"], list):
            # Ensure all artifacts are strings
            serialized_artifacts = []
            for artifact in result["artifacts"]:
                if isinstance(artifact, str):
                    serialized_artifacts.append(artifact)
                elif hasattr(artifact, '__str__'):
                    serialized_artifacts.append(str(artifact))
            result["artifacts"] = serialized_artifacts
        elif isinstance(result["artifacts"], str):
            # Convert single string to list
            result["artifacts"] = [result["artifacts"]]
        else:
            # Invalid type - convert to string
            result["artifacts"] = [str(result["artifacts"])]
    
    # Ensure other common artifact fields are also serialized
    for artifact_key in ["saved_files", "output_files", "plot_paths", "figure_paths"]:
        if artifact_key in result and result[artifact_key]:
            if isinstance(result[artifact_key], list):
                result[artifact_key] = [str(item) for item in result[artifact_key] if item]
            elif not isinstance(result[artifact_key], str):
                result[artifact_key] = str(result[artifact_key])
    
    # CRITICAL: Register model if this is a training tool
    # ALL model training tools MUST register their models globally
    if tool_context and result.get("model_path"):
        result = _register_trained_model(result, tool_context)
    
    # CRITICAL: Create markdown artifact for this tool (like plot does)
    # This ensures ALL tools save their output as viewable artifacts
    if tool_context:
        result = _create_tool_artifact(result, tool_name, tool_context)
    
    # Ensure ADK artifacts are created (for {artifact.filename} placeholders and LoadArtifactsTool)
    result = _ensure_artifacts_created(result, tool_name, tool_context)

    # EMERGENCY: Log if result key exists before we potentially modify it
    if isinstance(result, dict):
        has_result_key = "result" in result
        result_value = result.get("result")
        logger.error(f"[_ensure_ui_display] BEFORE result-key-check: has_result_key={has_result_key}, result_value_type={type(result_value)}, is_none={result_value is None}")

    # Provide a structured payload under `result` key for all tools (if not already present)
    if isinstance(result, dict) and "result" not in result:
        display_keys = {
            "__display__",
            "message",
            "ui_text",
            "text",
            "content",
            "display",
            "_formatted_output",
        }
        exclude_keys = display_keys | {
            "status",
            "result",
            "artifact_placeholders",
            "llm_artifact_enforcement",
        }

        payload = {}
        for key in list(result.keys()):
            if key in exclude_keys:
                continue
            value = result[key]
            if value is not None:
                payload[key] = value

        # DO NOT create nested result key - causes serialization issues
        # if payload:
        #     try:
        #         result["result"] = normalize_nested(payload)
        #     except Exception as e:
        #         logger.debug(f"[_ensure_ui_display] Failed to normalize result payload for {tool_name}: {e}")

    # DIAGNOSTIC: Log what we're returning
    _log_tool_result_diagnostics(result, tool_name, stage="output_from_ensure_ui_display")
    
    return result

# ===== CORE DATA SCIENCE TOOLS =====

def scale_data_tool(scaler: str = "StandardScaler", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for scale_data."""
    from .ds_tools import scale_data
    tool_context = kwargs.get("tool_context")
    csv_path = _resolve_csv_path(csv_path, tool_context, "scale_data")  # ✅ Use uploaded file
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # scale_data is async, must use _run_async
    result = _run_async(scale_data(scaler=scaler, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "scale_data", "raw_tool_output")
    return _ensure_ui_display(result, "scale_data", tool_context)

def encode_data_tool(encoder: str = "OneHotEncoder", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for encode_data."""
    from .ds_tools import encode_data
    tool_context = kwargs.get("tool_context")
    csv_path = _resolve_csv_path(csv_path, tool_context, "encode_data")  # ✅ Use uploaded file
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # encode_data is async, must use _run_async
    result = _run_async(encode_data(encoder=encoder, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "encode_data", "raw_tool_output")
    return _ensure_ui_display(result, "encode_data", tool_context)
    _log_tool_result_diagnostics(result, "encode_data", "raw_tool_output")
    return _ensure_ui_display(result, "encode_data", tool_context)

def expand_features_tool(method: str = "polynomial", degree: int = 2, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for expand_features."""
    from .ds_tools import expand_features
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # expand_features is async, must use _run_async
    result = _run_async(expand_features(method=method, degree=degree, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "expand_features", "raw_tool_output")
    return _ensure_ui_display(result, "expand_features", tool_context)

def impute_simple_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for impute_simple."""
    from .ds_tools import impute_simple
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # impute_simple is async, must use _run_async
    result = _run_async(impute_simple(csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "impute_simple", "raw_tool_output")
    return _ensure_ui_display(result, "impute_simple", tool_context)

def impute_knn_tool(n_neighbors: int = 5, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for impute_knn."""
    from .ds_tools import impute_knn
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # impute_knn is async, must use _run_async
    result = _run_async(impute_knn(n_neighbors=n_neighbors, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "impute_knn", "raw_tool_output")
    return _ensure_ui_display(result, "impute_knn", tool_context)

def impute_iterative_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for impute_iterative."""
    from .ds_tools import impute_iterative
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # impute_iterative is async, must use _run_async
    result = _run_async(impute_iterative(csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "impute_iterative", "raw_tool_output")
    return _ensure_ui_display(result, "impute_iterative", tool_context)


def robust_auto_clean_file_tool(
    csv_path: str = "",
    output_dir: str = "",
    force_header: str = "auto",
    datetime_infer: str = "yes",
    cap_outliers: str = "yes",
    impute_missing: str = "yes",
    drop_empty_columns: str = "yes",
    drop_duplicate_rows: str = "yes",
    keep_original_name: str = "yes",
    **kwargs,
) -> Dict[str, Any]:
    """ADK-safe wrapper for robust_auto_clean_file with artifact enforcement."""
    from .robust_auto_clean_file import robust_auto_clean_file as _robust_auto_clean_file

    tool_context = kwargs.get("tool_context")

    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT

        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = _robust_auto_clean_file(
        csv_path=csv_path,
        output_dir=output_dir,
        force_header=force_header,
        datetime_infer=datetime_infer,
        cap_outliers=cap_outliers,
        impute_missing=impute_missing,
        drop_empty_columns=drop_empty_columns,
        drop_duplicate_rows=drop_duplicate_rows,
        keep_original_name=keep_original_name,
        tool_context=tool_context,
    )

    _log_tool_result_diagnostics(result, "robust_auto_clean_file", "raw_tool_output")
    return _ensure_ui_display(result, "robust_auto_clean_file", tool_context)

def select_features_tool(target: str, k: int = 10, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for select_features."""
    from .ds_tools import select_features
    tool_context = kwargs.get("tool_context")
    csv_path = _resolve_csv_path(csv_path, tool_context, "select_features")  # ✅ Use uploaded file
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # select_features is async, must use _run_async
    result = _run_async(select_features(target=target, k=k, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "select_features", "raw_tool_output")
    return _ensure_ui_display(result, "select_features", tool_context)

def recursive_select_tool(target: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for recursive_select."""
    from .ds_tools import recursive_select
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # recursive_select is async, must use _run_async
    result = _run_async(recursive_select(target=target, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "recursive_select", "raw_tool_output")
    return _ensure_ui_display(result, "recursive_select", tool_context)

def sequential_select_tool(target: str, direction: str = "forward", n_features: int = 10, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for sequential_select."""
    from .ds_tools import sequential_select
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # sequential_select is async, must use _run_async
    result = _run_async(sequential_select(target=target, direction=direction, n_features=n_features, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "sequential_select", "raw_tool_output")
    return _ensure_ui_display(result, "sequential_select", tool_context)

def split_data_tool(target: str, test_size: float = 0.2, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for split_data."""
    from .ds_tools import split_data
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # split_data is async, must use _run_async
    result = _run_async(split_data(target=target, test_size=test_size, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "split_data", "raw_tool_output")
    return _ensure_ui_display(result, "split_data", tool_context)

def grid_search_tool(target: str, model: str, param_grid: str = "{}", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for grid_search."""
    from .ds_tools import grid_search
    import json
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    try:
        param_dict = json.loads(param_grid) if param_grid else {}
    except json.JSONDecodeError:
        param_dict = {}
    # grid_search is async, must use _run_async
    result = _run_async(grid_search(target=target, model=model, param_grid=param_dict, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "grid_search", "raw_tool_output")
    return _ensure_ui_display(result, "grid_search", tool_context)

def evaluate_tool(target: str, model: str, params: str = "{}", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for evaluate."""
    from .ds_tools import evaluate
    import json
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    try:
        params_dict = json.loads(params) if params else None
    except json.JSONDecodeError:
        params_dict = None
    result = _run_async(evaluate(target=target, model=model, params=params_dict, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "evaluate", "raw_tool_output")
    return _ensure_ui_display(result, "evaluate", tool_context)

def text_to_features_tool(text_col: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for text_to_features."""
    from .ds_tools import text_to_features
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # text_to_features is async, must use _run_async
    result = _run_async(text_to_features(text_col=text_col, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "text_to_features", "raw_tool_output")
    return _ensure_ui_display(result, "text_to_features", tool_context)

def load_existing_models_tool(dataset_name: str, **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for load_existing_models."""
    from .ds_tools import load_existing_models
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # load_existing_models is async, must use _run_async
    result = _run_async(load_existing_models(dataset_name=dataset_name, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "load_existing_models", "raw_tool_output")
    return _ensure_ui_display(result, "load_existing_models", tool_context)

# ===== ADVANCED TOOLS =====

def auto_feature_synthesis_tool(target: str, max_depth: int = 2, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for auto_feature_synthesis."""
    # Auto-install featuretools if missing
    try:
        from .auto_install_utils import ensure_tool_dependencies
        success, error_msg = ensure_tool_dependencies('auto_feature_synthesis', silent=False)
        if not success:
            return {
                "status": "error",
                "message": f"auto_feature_synthesis requires featuretools. {error_msg or 'Installation failed'}",
                "__display__": f"❌ auto_feature_synthesis() dependency not available.\n\n**Error:** {error_msg or 'Failed to install featuretools'}\n\n**Manual Installation:**\n```bash\npip install featuretools\n```\n\n**Alternative:** Use `expand_features()` or `select_features()` instead for feature engineering.",
                "ui_text": "Tool dependency missing - install featuretools",
                "text": "Tool dependency missing - install featuretools",
                "content": "Tool dependency missing - install featuretools"
            }
    except ImportError:
        # Fallback if auto_install_utils not available
        logger.warning("[AUTO_FEATURE_SYNTHESIS] auto_install_utils not available, skipping auto-install")
    
    # Import from extended_tools where it's actually defined
    try:
        from .extended_tools import auto_feature_synthesis
    except ImportError:
        # Fallback: try ds_tools (which conditionally imports from extended_tools)
        try:
            from .ds_tools import auto_feature_synthesis
        except ImportError:
            return {
                "status": "error",
                "message": "auto_feature_synthesis tool is not available. Please install featuretools: pip install featuretools",
                "__display__": "❌ auto_feature_synthesis() is not available in this environment.\n\nTo use this tool, you need to install Featuretools:\n```bash\npip install featuretools\n```\n\n**Alternative:** Use `expand_features()` or `select_features()` instead for feature engineering.",
                "ui_text": "Tool not available - install featuretools",
                "text": "Tool not available - install featuretools",
                "content": "Tool not available - install featuretools"
            }
    
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # Execute tool (handle async)
    try:
        import inspect
        if inspect.iscoroutinefunction(auto_feature_synthesis):
            coro = auto_feature_synthesis(target=target, max_depth=max_depth, csv_path=csv_path, tool_context=tool_context)
            result = _run_async(coro)
        else:
            result = auto_feature_synthesis(target=target, max_depth=max_depth, csv_path=csv_path, tool_context=tool_context)
    except Exception as e:
        logger.error(f"[AUTO_FEATURE_SYNTHESIS] Execution failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"auto_feature_synthesis failed: {str(e)}",
            "__display__": f"❌ auto_feature_synthesis() execution failed:\n\n{str(e)}\n\n**Possible solutions:**\n- Install featuretools: `pip install featuretools`\n- Ensure data file is valid CSV\n- Check that target column exists",
            "error": str(e)
        }
    
    _log_tool_result_diagnostics(result, "auto_feature_synthesis", "raw_tool_output")
    return _ensure_ui_display(result, "auto_feature_synthesis", tool_context)

def feature_importance_stability_tool(target: str, n_iterations: int = 5, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for feature_importance_stability."""
    from .ds_tools import feature_importance_stability
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = feature_importance_stability(target=target, n_iterations=n_iterations, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "feature_importance_stability", "raw_tool_output")
    return _ensure_ui_display(result, "feature_importance_stability", tool_context)

def apply_pca_tool(n_components: int = 2, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for apply_pca."""
    from .ds_tools import apply_pca
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # apply_pca is async, must use _run_async
    result = _run_async(apply_pca(n_components=n_components, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "apply_pca", "raw_tool_output")
    return _ensure_ui_display(result, "apply_pca", tool_context)

def train_baseline_model_tool(target: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for train_baseline_model."""
    from .ds_tools import train_baseline_model
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # train_baseline_model is async, must use _run_async
    result = _run_async(train_baseline_model(target=target, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "train_baseline_model", "raw_tool_output")
    return _ensure_ui_display(result, "train_baseline_model", tool_context)

def train_classifier_tool(target: str, model: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for train_classifier."""
    from .ds_tools import train_classifier
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # train_classifier is async, must use _run_async
    result = _run_async(train_classifier(target=target, model=model, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "train_classifier", "raw_tool_output")
    return _ensure_ui_display(result, "train_classifier", tool_context)

def train_regressor_tool(target: str, model: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for train_regressor."""
    from .ds_tools import train_regressor
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # train_regressor is async, must use _run_async
    result = _run_async(train_regressor(target=target, model=model, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "train_regressor", "raw_tool_output")
    return _ensure_ui_display(result, "train_regressor", tool_context)

def train_decision_tree_tool(target: str, max_depth: int = 3, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for train_decision_tree."""
    from .ds_tools import train_decision_tree
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # train_decision_tree is async, must use _run_async
    result = _run_async(train_decision_tree(target=target, max_depth=max_depth, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "train_decision_tree", "raw_tool_output")
    return _ensure_ui_display(result, "train_decision_tree", tool_context)

def train_knn_tool(target: str, n_neighbors: int = 5, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for train_knn."""
    from .ds_tools import train_knn
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # train_knn is async, must use _run_async
    result = _run_async(train_knn(target=target, n_neighbors=n_neighbors, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "train_knn", "raw_tool_output")
    return _ensure_ui_display(result, "train_knn", tool_context)

def train_naive_bayes_tool(target: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for train_naive_bayes."""
    from .ds_tools import train_naive_bayes
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # train_naive_bayes is async, must use _run_async
    result = _run_async(train_naive_bayes(target=target, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "train_naive_bayes", "raw_tool_output")
    return _ensure_ui_display(result, "train_naive_bayes", tool_context)

def train_svm_tool(target: str, kernel: str = "rbf", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for train_svm."""
    from .ds_tools import train_svm
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # train_svm is async, must use _run_async
    result = _run_async(train_svm(target=target, kernel=kernel, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "train_svm", "raw_tool_output")
    return _ensure_ui_display(result, "train_svm", tool_context)

def ensemble_tool(target: str, models: str = "[]", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for ensemble."""
    from .ds_tools import ensemble
    import json
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    try:
        models_list = json.loads(models) if models else []
    except json.JSONDecodeError:
        models_list = []
    # ensemble is async, must use _run_async
    result = _run_async(ensemble(target=target, models=models_list, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "ensemble", "raw_tool_output")
    return _ensure_ui_display(result, "ensemble", tool_context)

def explain_model_tool(model_name: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for explain_model."""
    from .ds_tools import explain_model
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # explain_model is async, must use _run_async
    result = _run_async(explain_model(model_name=model_name, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "explain_model", "raw_tool_output")
    return _ensure_ui_display(result, "explain_model", tool_context)

def anomaly_tool(method: str = "isolation_forest", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for anomaly."""
    from .ds_tools import anomaly
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # anomaly is async, must use _run_async
    result = _run_async(anomaly(method=method, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "anomaly", "raw_tool_output")
    return _ensure_ui_display(result, "anomaly", tool_context)

def export_tool(format: str = "csv", filename: str = "", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for export (async -> sync)."""
    from .ds_tools import export
    import asyncio
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # export is async, use _run_async for consistency
    result = _run_async(export(title=filename or "Data Science Analysis Report", csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "export", "raw_tool_output")
    return _ensure_ui_display(result, "export", tool_context)

def export_executive_report_tool(title: str = "Data Science Report", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for export_executive_report (async -> sync)."""
    from .ds_tools import export_executive_report
    import asyncio
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # export_executive_report is async, use _run_async for consistency
    result = _run_async(export_executive_report(project_title=title, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "export_executive_report", "raw_tool_output")
    return _ensure_ui_display(result, "export_executive_report", tool_context)

# ===== UNSTRUCTURED DATA TOOLS =====

def extract_text_tool(file_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for extract_text."""
    from .ds_tools import extract_text
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = extract_text(file_path=file_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "extract_text", "raw_tool_output")
    return _ensure_ui_display(result, "extract_text", tool_context)

def chunk_text_tool(text: str = "", chunk_size: int = 1000, overlap: int = 200, **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for chunk_text."""
    from .ds_tools import chunk_text
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = chunk_text(text=text, chunk_size=chunk_size, overlap=overlap, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "chunk_text", "raw_tool_output")
    return _ensure_ui_display(result, "chunk_text", tool_context)

def embed_and_index_tool(text_chunks: str = "[]", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for embed_and_index."""
    from .ds_tools import embed_and_index
    import json
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    try:
        chunks_list = json.loads(text_chunks) if text_chunks else []
    except json.JSONDecodeError:
        chunks_list = []
    result = embed_and_index(text_chunks=chunks_list, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "embed_and_index", "raw_tool_output")
    return _ensure_ui_display(result, "embed_and_index", tool_context)

def semantic_search_tool(query: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for semantic_search."""
    from .ds_tools import semantic_search
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = semantic_search(query=query, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "semantic_search", "raw_tool_output")
    return _ensure_ui_display(result, "semantic_search", tool_context)

def summarize_chunks_tool(chunks: str = "[]", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for summarize_chunks."""
    from .ds_tools import summarize_chunks
    import json
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    try:
        chunks_list = json.loads(chunks) if chunks else []
    except json.JSONDecodeError:
        chunks_list = []
    result = summarize_chunks(chunks=chunks_list, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "summarize_chunks", "raw_tool_output")
    return _ensure_ui_display(result, "summarize_chunks", tool_context)

def classify_text_tool(text: str = "", model: str = "sentiment", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for classify_text."""
    from .ds_tools import classify_text
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = classify_text(text=text, model=model, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "classify_text", "raw_tool_output")
    return _ensure_ui_display(result, "classify_text", tool_context)

def ingest_mailbox_tool(mailbox_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for ingest_mailbox."""
    from .ds_tools import ingest_mailbox
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = ingest_mailbox(mailbox_path=mailbox_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "ingest_mailbox", "raw_tool_output")
    return _ensure_ui_display(result, "ingest_mailbox", tool_context)

# ===== WORKSPACE & ARTIFACT TOOLS =====

def get_workspace_info_tool(**kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for get_workspace_info."""
    from .ds_tools import get_workspace_info
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = get_workspace_info(tool_context=tool_context)
    _log_tool_result_diagnostics(result, "get_workspace_info", "raw_tool_output")
    return _ensure_ui_display(result, "get_workspace_info", tool_context)

def create_dataset_workspace_tool(
    dataset_name: str = "",
    file_path: str = "",
    headers: str = "",
    context: str = "",
    **kwargs
) -> Dict[str, Any]:
    """ADK-safe wrapper for create_dataset_workspace - LLM can create organized workspace structures."""
    from .workspace_tools import create_dataset_workspace_tool as _create_workspace
    result = _create_workspace(
        dataset_name=dataset_name,
        file_path=file_path,
        headers=headers,
        context=context
    )
    tool_context = kwargs.get("tool_context")
    _log_tool_result_diagnostics(result, "create_dataset_workspace", "raw_tool_output")
    return _ensure_ui_display(result, "create_dataset_workspace", tool_context)

def save_file_to_workspace_tool(
    file_path: str = "",
    dataset_name: str = "",
    destination_name: str = "",
    file_type: str = "",
    **kwargs
) -> Dict[str, Any]:
    """ADK-safe wrapper for save_file_to_workspace - automatically organizes files by type."""
    from .workspace_tools import save_file_to_workspace_tool as _save_file
    result = _save_file(
        file_path=file_path,
        dataset_name=dataset_name,
        destination_name=destination_name,
        file_type=file_type
    )
    tool_context = kwargs.get("tool_context")
    _log_tool_result_diagnostics(result, "save_file_to_workspace", "raw_tool_output")
    return _ensure_ui_display(result, "save_file_to_workspace", tool_context)

def list_workspace_files_tool(
    dataset_name: str = "",
    file_type: str = "",
    **kwargs
) -> Dict[str, Any]:
    """ADK-safe wrapper for list_workspace_files - lists files in workspace by type."""
    from .workspace_tools import list_workspace_files_tool as _list_files
    result = _list_files(
        dataset_name=dataset_name,
        file_type=file_type
    )
    tool_context = kwargs.get("tool_context")
    _log_tool_result_diagnostics(result, "list_workspace_files", "raw_tool_output")
    return _ensure_ui_display(result, "list_workspace_files", tool_context)

def get_workspace_info_tool_v2(
    dataset_name: str = "",
    **kwargs
) -> Dict[str, Any]:
    """ADK-safe wrapper for get_workspace_info_v2 - gets workspace info by dataset name."""
    from .workspace_tools import get_workspace_info_tool as _get_info
    result = _get_info(dataset_name=dataset_name)
    tool_context = kwargs.get("tool_context")
    _log_tool_result_diagnostics(result, "get_workspace_info_v2", "raw_tool_output")
    return _ensure_ui_display(result, "get_workspace_info_v2", tool_context)

# ===== HYPERPARAMETER OPTIMIZATION =====

def optuna_tune_tool(target: str, model: str, n_trials: int = 10, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for optuna_tune."""
    from .ds_tools import optuna_tune
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = optuna_tune(target=target, model=model, n_trials=n_trials, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "optuna_tune", "raw_tool_output")
    return _ensure_ui_display(result, "optuna_tune", tool_context)

# ===== DATA VALIDATION & QUALITY =====

def ge_auto_profile_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for ge_auto_profile."""
    from .ds_tools import ge_auto_profile
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = ge_auto_profile(csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "ge_auto_profile", "raw_tool_output")
    return _ensure_ui_display(result, "ge_auto_profile", tool_context)

def ge_validate_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for ge_validate."""
    from .ds_tools import ge_validate
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = ge_validate(csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "ge_validate", "raw_tool_output")
    return _ensure_ui_display(result, "ge_validate", tool_context)

def data_quality_report_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for data_quality_report."""
    from .ds_tools import data_quality_report
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = data_quality_report(csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "data_quality_report", "raw_tool_output")
    return _ensure_ui_display(result, "data_quality_report", tool_context)

# ===== EXPERIMENT TRACKING =====

def mlflow_start_run_tool(experiment_name: str = "default", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for mlflow_start_run."""
    from .ds_tools import mlflow_start_run
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = mlflow_start_run(experiment_name=experiment_name, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "mlflow_start_run", "raw_tool_output")
    return _ensure_ui_display(result, "mlflow_start_run", tool_context)

def mlflow_log_metrics_tool(metrics: str = "{}", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for mlflow_log_metrics."""
    from .ds_tools import mlflow_log_metrics
    import json
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    try:
        metrics_dict = json.loads(metrics) if metrics else {}
    except json.JSONDecodeError:
        metrics_dict = {}
    result = mlflow_log_metrics(metrics=metrics_dict, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "mlflow_log_metrics", "raw_tool_output")
    return _ensure_ui_display(result, "mlflow_log_metrics", tool_context)

def mlflow_end_run_tool(**kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for mlflow_end_run."""
    from .ds_tools import mlflow_end_run
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    _log_tool_result_diagnostics(result, "mlflow_end_run", "raw_tool_output")
    return _ensure_ui_display(mlflow_end_run(tool_context=tool_context), "mlflow_end_run", tool_context)

def export_model_card_tool(model_name: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for export_model_card."""
    from .ds_tools import export_model_card
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = export_model_card(model_name=model_name, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "export_model_card", "raw_tool_output")
    return _ensure_ui_display(result, "export_model_card", tool_context)

# ===== RESPONSIBLE AI =====

def fairness_report_tool(target: str, sensitive_features: str = "[]", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for fairness_report."""
    from .ds_tools import fairness_report
    import json
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    try:
        features_list = json.loads(sensitive_features) if sensitive_features else []
    except json.JSONDecodeError:
        features_list = []
    result = fairness_report(target=target, sensitive_features=features_list, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "fairness_report", "raw_tool_output")
    return _ensure_ui_display(result, "fairness_report", tool_context)

def fairness_mitigation_grid_tool(target: str, sensitive_features: str = "[]", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for fairness_mitigation_grid."""
    from .ds_tools import fairness_mitigation_grid
    import json
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    try:
        features_list = json.loads(sensitive_features) if sensitive_features else []
    except json.JSONDecodeError:
        features_list = []
    result = fairness_mitigation_grid(target=target, sensitive_features=features_list, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "fairness_mitigation_grid", "raw_tool_output")
    return _ensure_ui_display(result, "fairness_mitigation_grid", tool_context)

# ===== DRIFT DETECTION =====

def drift_profile_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for drift_profile."""
    from .ds_tools import drift_profile
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = drift_profile(csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "drift_profile", "raw_tool_output")
    return _ensure_ui_display(result, "drift_profile", tool_context)

# ===== CAUSAL INFERENCE =====

def causal_identify_tool(target: str, treatment: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for causal_identify."""
    from .ds_tools import causal_identify
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = causal_identify(target=target, treatment=treatment, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "causal_identify", "raw_tool_output")
    return _ensure_ui_display(result, "causal_identify", tool_context)

def causal_estimate_tool(target: str, treatment: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for causal_estimate."""
    from .ds_tools import causal_estimate
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = causal_estimate(target=target, treatment=treatment, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "causal_estimate", "raw_tool_output")
    return _ensure_ui_display(result, "causal_estimate", tool_context)

# ===== TIME SERIES =====

def ts_prophet_forecast_tool(target: str, date_col: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for ts_prophet_forecast."""
    from .ds_tools import ts_prophet_forecast
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = ts_prophet_forecast(target=target, date_col=date_col, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "ts_prophet_forecast", "raw_tool_output")
    return _ensure_ui_display(result, "ts_prophet_forecast", tool_context)

def ts_backtest_tool(target: str, date_col: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for ts_backtest."""
    from .ds_tools import ts_backtest
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = ts_backtest(target=target, date_col=date_col, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "ts_backtest", "raw_tool_output")
    return _ensure_ui_display(result, "ts_backtest", tool_context)

def smart_autogluon_timeseries_tool(target: str, date_col: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for smart_autogluon_timeseries."""
    from .ds_tools import smart_autogluon_timeseries
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = smart_autogluon_timeseries(target=target, date_col=date_col, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "smart_autogluon_timeseries", "raw_tool_output")
    return _ensure_ui_display(result, "smart_autogluon_timeseries", tool_context)

# ===== ADVANCED MODELING =====
# Note: auto_feature_synthesis_tool is defined earlier (line 994) - no duplicate needed

def train_tool(target: str, model: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for train."""
    from .ds_tools import train
    tool_context = kwargs.get("tool_context")
    csv_path = _resolve_csv_path(csv_path, tool_context, "train")  # ✅ Use uploaded file
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = _run_async(train(target=target, model=model, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "train", "raw_tool_output")
    return _ensure_ui_display(result, "train", tool_context)

def predict_tool(target: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """
    ADK-safe wrapper for predict.
    
    Trains a model for the specified target and returns formatted predictions.
    Results are displayed in the UI and saved to workspace for inclusion in executive reports.
    
    Args:
        target: The column to predict (e.g., 'price', 'sales', 'revenue')
        csv_path: Optional path to CSV file (auto-detected if not provided)
        **kwargs: Additional arguments including tool_context
    
    Returns:
        Dict with predictions, metrics, and formatted UI display
    """
    from .ds_tools import predict
    tool_context = kwargs.get("tool_context")
    csv_path = _resolve_csv_path(csv_path, tool_context, "predict")  # ✅ Use uploaded file
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = _run_async(predict(target=target, csv_path=csv_path, tool_context=tool_context))
    
    # Ensure all display fields are present (predict already adds them, but double-check)
    if isinstance(result, dict) and "__display__" not in result:
        msg = result.get("message") or result.get("text") or "Prediction complete"
        result["__display__"] = msg
        result["text"] = msg
        result["message"] = msg
        result["ui_text"] = msg
        result["content"] = msg
    
    _log_tool_result_diagnostics(result, "predict", "raw_tool_output")
    return _ensure_ui_display(result, "predict", tool_context)

def classify_tool(model_name: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for classify."""
    from .ds_tools import classify
    tool_context = kwargs.get("tool_context")
    csv_path = _resolve_csv_path(csv_path, tool_context, "classify")  # ✅ Use uploaded file
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # classify is async, must use _run_async
    result = _run_async(classify(model_name=model_name, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "classify", "raw_tool_output")
    return _ensure_ui_display(result, "classify", tool_context)

def accuracy_tool(model_name: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for accuracy."""
    from .ds_tools import accuracy
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # accuracy is async, must use _run_async
    result = _run_async(accuracy(model_name=model_name, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "accuracy", "raw_tool_output")
    return _ensure_ui_display(result, "accuracy", tool_context)

def load_model_tool(model_name: str, **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for load_model."""
    from .ds_tools import load_model
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # load_model is async, must use _run_async
    result = _run_async(load_model(model_name=model_name, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "load_model", "raw_tool_output")
    return _ensure_ui_display(result, "load_model", tool_context)

# ===== CLUSTERING =====

def smart_cluster_tool(n_clusters: int = 3, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for smart_cluster."""
    from .ds_tools import smart_cluster
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # smart_cluster is async, must use _run_async
    result = _run_async(smart_cluster(n_clusters=n_clusters, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "smart_cluster", "raw_tool_output")
    return _ensure_ui_display(result, "smart_cluster", tool_context)

def kmeans_cluster_tool(n_clusters: int = 3, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for kmeans_cluster."""
    from .ds_tools import kmeans_cluster
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # kmeans_cluster is async, must use _run_async
    result = _run_async(kmeans_cluster(n_clusters=n_clusters, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "kmeans_cluster", "raw_tool_output")
    return _ensure_ui_display(result, "kmeans_cluster", tool_context)

def dbscan_cluster_tool(eps: float = 0.5, min_samples: int = 5, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for dbscan_cluster."""
    from .ds_tools import dbscan_cluster
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # dbscan_cluster is async, must use _run_async
    result = _run_async(dbscan_cluster(eps=eps, min_samples=min_samples, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "dbscan_cluster", "raw_tool_output")
    return _ensure_ui_display(result, "dbscan_cluster", tool_context)

def hierarchical_cluster_tool(n_clusters: int = 3, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for hierarchical_cluster."""
    from .ds_tools import hierarchical_cluster
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # hierarchical_cluster is async, must use _run_async
    result = _run_async(hierarchical_cluster(n_clusters=n_clusters, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "hierarchical_cluster", "raw_tool_output")
    return _ensure_ui_display(result, "hierarchical_cluster", tool_context)

def isolation_forest_train_tool(contamination: float = 0.1, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for isolation_forest_train."""
    from .ds_tools import isolation_forest_train
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # isolation_forest_train is async, must use _run_async
    result = _run_async(isolation_forest_train(contamination=contamination, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "isolation_forest_train", "raw_tool_output")
    return _ensure_ui_display(result, "isolation_forest_train", tool_context)

# ===== STATISTICAL ANALYSIS =====

def stats_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for stats."""
    from .ds_tools import stats
    from .utils.paths import ensure_workspace, resolve_csv
    from .utils.io import robust_read_table  # noqa: F401
    from pathlib import Path
    import logging
    logger = logging.getLogger(__name__)
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # ✅ CRITICAL FIX: Use uploaded file from state if available
    if not csv_path and state:
        try:
            default_csv_from_state = state.get("default_csv_path")
            force_default = state.get("force_default_csv", False)
            if force_default and default_csv_from_state:
                csv_path = default_csv_from_state
                logger.info(f"[STATS] Using uploaded file from state: {Path(csv_path).name}")
        except Exception as e:
            logger.warning(f"[STATS] Could not read uploaded file from state: {e}")

    try:
        dataset_slug, ws, default_csv = ensure_workspace(csv_path or None)
        resolved = resolve_csv(csv_path or default_csv, dataset_slug=dataset_slug)
        result = _run_async(stats(csv_path=str(resolved), tool_context=tool_context))
    except Exception:
        result = _run_async(stats(csv_path=csv_path, tool_context=tool_context))
    
    # Stats already returns properly formatted display fields, just ensure they exist
    if isinstance(result, dict):
        # Stats function already adds all display fields - just verify they exist
        if "__display__" not in result or not result["__display__"]:
            msg = result.get("message") or result.get("text") or result.get("content") or ""
            if msg:
                result["__display__"] = msg
                result["message"] = msg
                result["text"] = msg
                result["ui_text"] = msg
                result["content"] = msg
                result["display"] = msg
                result["_formatted_output"] = msg
    
    _log_tool_result_diagnostics(result, "stats", "raw_tool_output")
    return _ensure_ui_display(result, "stats", tool_context)

# ===== RECOMMENDATION =====

def recommend_model_tool(target: str = "", csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for recommend_model.
    
    **AUTO-TARGET DETECTION:** If target is empty, recommend_model() will auto-detect the best target variable.
    """
    from .ds_tools import recommend_model
    tool_context = kwargs.get("tool_context")
    csv_path = _resolve_csv_path(csv_path, tool_context, "recommend_model")  # ✅ Use uploaded file
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # recommend_model is async, must use _run_async
    # CRITICAL: target can be empty - recommend_model will auto-detect
    result = _run_async(recommend_model(target=target if target else None, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "recommend_model", "raw_tool_output")
    return _ensure_ui_display(result, "recommend_model", tool_context)

def suggest_next_steps_tool(**kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for suggest_next_steps."""
    from .ds_tools import suggest_next_steps
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    _log_tool_result_diagnostics(result, "suggest_next_steps", "raw_tool_output")
    return _ensure_ui_display(suggest_next_steps(tool_context=tool_context), "suggest_next_steps", tool_context)

def execute_next_step_tool(step: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for execute_next_step."""
    from .ds_tools import execute_next_step
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # Map string/number to integer option
    try:
        opt = int(step)
    except Exception:
        # Allow keywords
        mapping = {
            "export": 1,
            "export_executive_report": 2,
            "plot": 3,
            "smart_cluster": 4,
            "ensemble": 5,
            "explain_model": 6,
            "load_model": 7,
        }
        opt = mapping.get((step or "").strip().lower(), 0)
    # execute_next_step is async, must use _run_async
    result = _run_async(execute_next_step(option_number=opt, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "execute_next_step", "raw_tool_output")
    return _ensure_ui_display(result, "execute_next_step", tool_context)

# ===== FILE MANAGEMENT =====

def list_data_files_tool(**kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for list_data_files."""
    from .ds_tools import list_data_files
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # list_data_files is async, must use _run_async
    result = _run_async(list_data_files(tool_context=tool_context))
    _log_tool_result_diagnostics(result, "list_data_files", "raw_tool_output")

    # CRITICAL: Ensure __display__ is preserved (contains formatted filenames, not MIME types)
    # Don't let _ensure_ui_display overwrite it with generic content
    display_text = None
    if isinstance(result, dict) and result.get("__display__"):
        # Preserve the formatted display text from list_data_files
        display_text = result.get("__display__")
        result.setdefault("message", display_text)
        result.setdefault("ui_text", display_text)
        result.setdefault("text", display_text)
        result.setdefault("content", display_text)
    
    # Normalize for UI (guarantees __display__ and other fields)
    final_result = _ensure_ui_display(result, "list_data_files", tool_context)
    
    # CRITICAL: After _ensure_ui_display, re-assert __display__ if it got overwritten
    if display_text and isinstance(final_result, dict):
        if not final_result.get("__display__") or final_result.get("__display__") != display_text:
            final_result["__display__"] = display_text
            final_result["message"] = display_text
            final_result["ui_text"] = display_text

    # --- Force-publish to UI immediately (pre-callback) ---
    try:
        from .callbacks import _as_blocks, publish_ui_blocks
        blocks = _as_blocks("list_data_files_tool", final_result)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            fut = asyncio.run_coroutine_threadsafe(
                publish_ui_blocks(tool_context, "list_data_files_tool", blocks), loop
            )
            fut.result(timeout=30)
        except RuntimeError:
            asyncio.run(publish_ui_blocks(tool_context, "list_data_files_tool", blocks))
        except Exception as e:
            logger.error(f"[list_data_files_tool] UI publish failed: {e}")
    except Exception as e:
        logger.debug(f"[list_data_files_tool] Skipping pre-callback UI publish: {e}")

    # --- Save guaranteed Markdown artifact via ADK artifact service ---
    try:
        display_text = None
        if isinstance(final_result, dict):
            display_text = (
                final_result.get("__display__")
                or final_result.get("message")
                or final_result.get("ui_text")
                or final_result.get("text")
                or final_result.get("content")
            )

        from datetime import datetime
        from google.genai import types
        md_body = f"# list_data_files\n\n{display_text or 'list_data_files completed successfully.'}\n"
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        md_name = f"tool_executions/{stamp}_list_data_files_tool.md"
        blob = types.Blob(data=md_body.encode("utf-8"), mime_type="text/markdown")
        part = types.Part(inline_data=blob)

        import asyncio as _aio
        import concurrent.futures as _cf
        if tool_context is not None:
            try:
                loop = _aio.get_running_loop()
                with _cf.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_aio.run, tool_context.save_artifact(md_name, part))
                    fut.result(timeout=10)
            except RuntimeError:
                _aio.run(tool_context.save_artifact(md_name, part))

            # Ensure artifact is listed in the result
            if isinstance(final_result, dict):
                final_result.setdefault("artifacts", []).append(md_name)
                final_result.setdefault("files", []).append(md_name)
    except Exception as e:
        logger.debug(f"[list_data_files_tool] Skipped markdown artifact save: {e}")

    return final_result

def save_uploaded_file_tool(filename: str = "", content: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for save_uploaded_file."""
    from .ds_tools import save_uploaded_file
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # save_uploaded_file is async, must use _run_async
    result = _run_async(save_uploaded_file(filename=filename, content=content, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "save_uploaded_file", "raw_tool_output")
    return _ensure_ui_display(result, "save_uploaded_file", tool_context)

def list_available_models_tool(**kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for list_available_models - now uses global model registry."""
    from .model_registry import list_models, load_registry_from_disk
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    workspace_root = None
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            workspace_root = state.get('workspace_root')
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {workspace_root}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")
    
    # Load registry from disk if available
    if workspace_root:
        load_registry_from_disk(workspace_root)
    
    # Get list of models
    models = list_models()
    
    if not models:
        result = {
            "status": "success",
            "message": "No trained models found in registry. Train a model first.",
            "models": [],
            "count": 0
        }
    else:
        # Format models for display
        model_list = []
        for model in models:
            model_list.append({
                "name": model["model_name"],
                "type": model["model_type"],
                "target": model["target"],
                "path": model["model_path"],
                "registered": model["registered_at"]
            })
        
        message_parts = [f"## Registered Models ({len(models)})\n"]
        for m in model_list:
            message_parts.append(f"\n### {m['name']}\n")
            message_parts.append(f"- **Type:** {m['type']}\n")
            message_parts.append(f"- **Target:** {m['target']}\n")
            message_parts.append(f"- **Path:** `{m['path']}`\n")
            message_parts.append(f"- **Registered:** {m['registered']}\n")
        
        result = {
            "status": "success",
            "message": "\n".join(message_parts),
            "models": model_list,
            "count": len(models)
        }
    
    _log_tool_result_diagnostics(result, "list_available_models", "raw_tool_output")
    return _ensure_ui_display(result, "list_available_models", tool_context)

# ===== AUTO-SKLEARN =====

def auto_sklearn_classify_tool(target: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for auto_sklearn_classify."""
    from .ds_tools import auto_sklearn_classify
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = auto_sklearn_classify(target=target, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "auto_sklearn_classify", "raw_tool_output")
    return _ensure_ui_display(result, "auto_sklearn_classify", tool_context)

def auto_sklearn_regress_tool(target: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for auto_sklearn_regress."""
    from .ds_tools import auto_sklearn_regress
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = auto_sklearn_regress(target=target, csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "auto_sklearn_regress", "raw_tool_output")
    return _ensure_ui_display(result, "auto_sklearn_regress", tool_context)

# ===== ANALYSIS & VISUALIZATION =====

def analyze_dataset_tool(
    csv_path: str = "",
    target: str = "",
    task: str = "",
    datetime_col: str = "",
    index_col: str = "",
    sample_rows: int = 5,
    **kwargs
) -> Dict[str, Any]:
    """ADK-safe wrapper for analyze_dataset."""
    from .ds_tools import analyze_dataset
    import logging
    from pathlib import Path
    from .utils.paths import ensure_workspace, resolve_csv
    from .utils.io import robust_read_table
    logger = logging.getLogger(__name__)
    
    tool_context = kwargs.get("tool_context")
    
    # Initialize result to avoid undefined variable
    result = None
    csv_for_children = csv_path
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    
    # ===== CRITICAL: Setup artifact manager (like plot() does) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception:
            pass
        artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
        logger.info(f"[ANALYZE_DATASET] ✓ Artifact manager ensured workspace: {state.get('workspace_root')}")
    except Exception as e:
        logger.warning(f"[ANALYZE_DATASET] ⚠ Failed to ensure workspace: {e}")
    
    # ✅ CRITICAL FIX: Use uploaded file from state if available
    if not csv_path and state:
        try:
            default_csv_from_state = state.get("default_csv_path")
            force_default = state.get("force_default_csv", False)
            if force_default and default_csv_from_state:
                csv_path = default_csv_from_state
                logger.info(f"[ANALYZE_DATASET] Using uploaded file from state: {Path(csv_path).name}")
                print(f"[OK] Using uploaded file: {Path(csv_path).name}")
        except Exception as e:
            logger.warning(f"[ANALYZE_DATASET] Could not read uploaded file from state: {e}")
    
    # Resolve via workspace first
    try:
        dataset_slug, ws, default_csv = ensure_workspace(csv_path or None)
        resolved = resolve_csv(csv_path or default_csv, dataset_slug=dataset_slug)

        # CSV only
        safe_path = Path(resolved)
        
        # Reject Parquet files (CSV only)
        if safe_path.suffix.lower() == ".parquet":
            raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {safe_path.name}")
        
        # If we got CSV, create a UTF-8 safe copy if needed
        if safe_path.suffix.lower() == ".csv":
            try:
                df = robust_read_table(resolved)
                # Create UTF-8 CSV copy in cache for consistency
                cache_dir = ws / "cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                safe_csv = cache_dir / f"{safe_path.stem}.utf8.csv"
                if not safe_csv.exists():
                    df.to_csv(safe_csv, index=False, encoding="utf-8")
                    logger.info(f"[analyze_dataset_tool] ✅ Created UTF-8 CSV copy: {safe_csv.name}")
                safe_path = safe_csv
            except Exception as e:
                logger.warning(f"[analyze_dataset_tool] robust_read_table failed ({e}); proceeding with original path")

        result = _run_async(
            analyze_dataset(
                csv_path=str(safe_path),
                target=target,
                task=task,
                datetime_col=datetime_col,
                index_col=index_col,
                sample_rows=sample_rows,
                tool_context=tool_context,
            )
        )
        csv_for_children = str(safe_path)
        logger.info(f"[analyze_dataset_tool] Primary path succeeded, result type: {type(result)}")
        
        # EMERGENCY DIAGNOSTIC: Log EXACT result from analyze_dataset
        logger.debug(f"[analyze_dataset_tool] Result keys: {list(result.keys()) if isinstance(result, dict) else 'NOT_DICT'}")
        if isinstance(result, dict):
            if 'result' in result:
                logger.debug(f"[analyze_dataset_tool] Nested result key present")
            if '__display__' in result:
                logger.debug(f"[analyze_dataset_tool] __display__ length: {len(str(result.get('__display__', '')))}")
            if 'message' in result:
                logger.debug(f"[analyze_dataset_tool] message length: {len(str(result.get('message', '')))}")
        
        # DIAGNOSTIC: Log what analyze_dataset returned
        _log_tool_result_diagnostics(result, "analyze_dataset", stage="primary_path_result")
    except Exception as e:
        # Fallback path resolution; still attempt robust read/write when possible
        logger.warning(f"[analyze_dataset_tool] Primary path failed: {e}, trying fallback")
        csv_for_children = csv_path
        try:
            if csv_path:
                df = robust_read_table(csv_path)
                # Write a local UTF-8 safe copy next to original
                p = Path(csv_path)
                safe_csv = p.with_suffix("")
                safe_csv = safe_csv.with_name(f"{safe_csv.name}.utf8.csv")
                df.to_csv(safe_csv, index=False, encoding="utf-8")
                csv_for_children = str(safe_csv)
        except Exception as e2:
            logger.warning(f"[analyze_dataset_tool] Fallback CSV conversion failed: {e2}")
        
        try:
            result = _run_async(
                analyze_dataset(
                    csv_path=csv_for_children,
                    target=target,
                    task=task,
                    datetime_col=datetime_col,
                    index_col=index_col,
                    sample_rows=sample_rows,
                    tool_context=tool_context,
                )
            )
            logger.info(f"[analyze_dataset_tool] Fallback path succeeded, result type: {type(result)}")
            # DIAGNOSTIC: Log what analyze_dataset returned from fallback
            _log_tool_result_diagnostics(result, "analyze_dataset", stage="fallback_path_result")
        except Exception as e3:
            logger.error(f"[analyze_dataset_tool] Both analyze_dataset attempts failed: {e3}", exc_info=True)
            # CRITICAL: Return a proper error result so user is notified
            error_message = str(e3)
            if "CSV not found" in error_message or "FileNotFoundError" in str(type(e3).__name__):
                error_message = (
                    "**❌ CSV File Not Found**\n\n"
                    "The dataset file could not be found. Please:\n\n"
                    "1. **Upload a CSV file** through the UI\n"
                    "2. **Check the file path** - ensure it's in the workspace uploads folder\n"
                    "3. **Use `list_data_files_tool()`** to see available files\n\n"
                    f"**Technical Error:** {error_message}\n\n"
                    "**Workspace:** The workspace was created but no CSV file was found in it."
                )
            else:
                error_message = (
                    f"**❌ Dataset Analysis Failed**\n\n"
                    f"**Error:** {error_message}\n\n"
                    "Please check the logs for details or try uploading the file again."
                )
            
            result = {
                "status": "failed",
                "error": True,
                "__error__": True,
                "error_message": error_message,
                "__display__": error_message,
                "message": error_message,
                "ui_text": error_message,
                "text": error_message,
                "content": error_message
            }
    
    # Automatically run head and describe after analysis
    # Only proceed if we have a valid result
    if result is not None and isinstance(result, dict):
        try:
            from .head_describe_guard import head_tool_guard, describe_tool_guard
            
            logger.info(f"[analyze_dataset_tool] Running head/describe with csv_path={csv_for_children}")
            
            # Pass csv_path to ensure head/describe have the right data
            # Run head tool
            head_result = head_tool_guard(tool_context=tool_context, csv_path=csv_for_children, **kwargs)
            logger.info(f"[analyze_dataset_tool] head_result keys: {list(head_result.keys()) if isinstance(head_result, dict) else 'N/A'}")
            logger.info(f"[analyze_dataset_tool] head_result message length: {len(head_result.get('message', '')) if isinstance(head_result, dict) else 0}")
            
            # Run describe tool  
            describe_result = describe_tool_guard(tool_context=tool_context, csv_path=csv_for_children, **kwargs)
            logger.info(f"[analyze_dataset_tool] describe_result keys: {list(describe_result.keys()) if isinstance(describe_result, dict) else 'N/A'}")
            logger.info(f"[analyze_dataset_tool] describe_result message length: {len(describe_result.get('message', '')) if isinstance(describe_result, dict) else 0}")
            
            # Combine results into a rich message
            msg_parts = []

            # Add analyze_dataset message if it exists (with sanitization)
            if isinstance(result, dict) and result.get("message"):
                from .agent import sanitize_text
                analyze_msg = sanitize_text(str(result["message"]), ascii_only=False, max_len=3000)
                msg_parts.append(analyze_msg)

            # Add head preview if available (with sanitization)
            if isinstance(head_result, dict) and head_result.get("message"):
                from .agent import sanitize_text
                head_msg = sanitize_text(str(head_result["message"]), ascii_only=False, max_len=3000)
                msg_parts.append(head_msg)
                logger.info(f"[analyze_dataset_tool] Added head message to output (sanitized)")

            # Add describe stats if available (with sanitization)
            if isinstance(describe_result, dict) and describe_result.get("message"):
                from .agent import sanitize_text
                desc_msg = sanitize_text(str(describe_result["message"]), ascii_only=False, max_len=3000)
                msg_parts.append(desc_msg)
                logger.info(f"[analyze_dataset_tool] Added describe message to output (sanitized)")

            if msg_parts:
                combined = "\n\n".join([m for m in msg_parts if m])
                loud_message = (
                    "📊 **Dataset Analysis Complete!**\n\n"
                    f"{combined}\n\n"
                    "✅ **Ready for next steps** - See recommended options above!"
                )
                
                # CRITICAL: Also ensure the full detailed content is saved to artifact
                # The wrapper creates a combined message, but we need to save the FULL content that appears in console
                if tool_context and loud_message:
                    try:
                        from google.genai import types
                        # Save the FULL combined message (not just the minimal analyze_dataset output)
                        detailed_md = f"# Dataset Analysis Results\n\n{loud_message}\n\n---\n\n## Full Analysis Details\n\n{combined}"
                        # CRITICAL: Sanitize to remove control characters and binary garbage
                        from .agent import sanitize_text
                        detailed_md = sanitize_text(detailed_md, ascii_only=False, max_len=10000)
                        loud_message = sanitize_text(loud_message, ascii_only=False, max_len=5000)
                        combined = sanitize_text(combined, ascii_only=False, max_len=5000)
                        # Save with explicit UTF-8 encoding
                        _run_async(tool_context.save_artifact(
                            filename="reports/analyze_dataset_combined.md",
                            artifact=types.Part.from_bytes(
                                data=detailed_md.encode('utf-8', errors='replace'),
                                mime_type="text/markdown"
                            ),
                        ))
                        logger.info(f"[analyze_dataset_tool] ✅ Saved combined detailed markdown artifact")
                    except Exception as artifact_err:
                        logger.warning(f"[analyze_dataset_tool] Failed to save combined artifact: {artifact_err}")

                # Preserve the full analysis output but ensure JSON safety
                normalized_result = normalize_nested(result if isinstance(result, dict) else {})

                # Attach head/describe structured outputs for programmatic access
                if isinstance(head_result, dict):
                    normalized_result["head_preview"] = normalize_nested(head_result)
                if isinstance(describe_result, dict):
                    normalized_result["describe_summary"] = normalize_nested(describe_result)

                normalized_result["status"] = normalized_result.get("status", "success")
                for field_name in [
                    "__display__",
                    "message",
                    "text",
                    "ui_text",
                    "content",
                    "display",
                    "_formatted_output",
                ]:
                    normalized_result[field_name] = loud_message

                # Preserve artifacts if present
                if "artifacts" in result:
                    normalized_result["artifacts"] = normalize_nested(result["artifacts"])

                result = normalized_result
                logger.info(f"[analyze_dataset_tool] Final combined message length: {len(loud_message)}")
                logger.info(f"[analyze_dataset_tool] Message preview: {loud_message[:200]}...")
            else:
                # Fallback message if nothing was generated
                fallback_msg = (
                    "⚠️ **Dataset analysis complete** but no data preview generated. "
                    "Try running `head()` or `describe()` manually."
                )
                normalized_result = normalize_nested(result if isinstance(result, dict) else {})
                normalized_result["status"] = normalized_result.get("status", "success")
                for field_name in [
                    "__display__",
                    "message",
                    "text",
                    "ui_text",
                    "content",
                    "display",
                    "_formatted_output",
                ]:
                    normalized_result[field_name] = fallback_msg
                result = normalized_result
                logger.warning(f"[analyze_dataset_tool] No messages generated, using fallback")
            
        except Exception as e:
            logger.warning(f"Auto head/describe failed: {e}", exc_info=True)
    else:
        logger.warning(f"[analyze_dataset_tool] Skipping head/describe - result is None or not a dict")
    
    # [OK] ENSURE result always has a message field with __display__
    if result is None:
        # If result is still None, create an error response (already clean)
        error_msg = "❌ **Dataset analysis failed** - Unable to analyze the dataset. Please check the file path and format."
        result = normalize_nested({
            "status": "failed",
            "__display__": error_msg,
            "message": error_msg,
            "text": error_msg,
            "ui_text": error_msg,
            "content": error_msg,
            "display": error_msg,
            "_formatted_output": error_msg,
            "error": "Result was None - analyze_dataset may have failed"
        })
        logger.error("[analyze_dataset_tool] Result is None - this indicates analyze_dataset failed")
    elif isinstance(result, dict) and not result.get("message"):
        # Let _ensure_ui_display handle extracting data from result key
        # Don't override with generic message - let the data show through
        result = normalize_nested(result)
    
    # Log the result status
    logger.info(f"[analyze_dataset_tool] Returning result with status: {result.get('status') if isinstance(result, dict) else 'unknown'}")
    logger.info(f"[analyze_dataset_tool] Result has __display__: {bool(result.get('__display__')) if isinstance(result, dict) else False}")
    
    # CRITICAL: Test JSON serializability BEFORE returning
    # If it fails, the callback will replace with minimal fallback
    try:
        import json
        json.dumps(result)
        logger.info(f"[analyze_dataset_tool] Result is JSON-serializable - good to go")
    except Exception as json_err:
        logger.error(f"[analyze_dataset_tool] Result is NOT JSON-serializable: {json_err}")
        logger.error(f"[analyze_dataset_tool] Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        # Try to identify which field is problematic
        if isinstance(result, dict):
            for key, value in result.items():
                try:
                    json.dumps({key: value})
                except Exception as e:
                    logger.error(f"[analyze_dataset_tool] Non-serializable field: {key} = {type(value)}: {str(e)[:100]}")
    
    # CRITICAL: Call _ensure_ui_display for proper artifact creation and diagnostic logging
    _log_tool_result_diagnostics(result, "analyze_dataset", stage="raw_tool_output")
    final_result = _ensure_ui_display(result, "analyze_dataset", tool_context)
    
    # EMERGENCY FIX: Ensure __display__ field is ALWAYS present and NOT empty
    # This is the ONLY way to get content into the markdown files
    if isinstance(final_result, dict):
        # Check if __display__ is missing or empty
        if not final_result.get("__display__"):
            # Try to extract from any display field
            display_content = (
                final_result.get("message") or 
                final_result.get("ui_text") or 
                final_result.get("text") or 
                final_result.get("content") or
                "✅ Dataset analysis completed. Check artifacts for results."
            )
            # Set ALL display fields to ensure at least one is picked up
            for field in ["__display__", "message", "ui_text", "text", "content", "display", "_formatted_output"]:
                final_result[field] = display_content
            logger.debug(f"[analyze_dataset_tool] Injected display content ({len(display_content)} chars)")
        else:
            logger.debug(f"[analyze_dataset_tool] __display__ already present ({len(final_result.get('__display__', ''))} chars)")
        
        # CRITICAL: After successful analyze_dataset, ALWAYS ensure results are prominently displayed and present the next menu
        # Even if tool_context is None, we should still show a menu (with fallback)
        # IMPORTANT: This MUST run AFTER _ensure_ui_display to append menu to the final result
        if final_result.get("status") == "success":
            # Ensure __display__ contains the full analysis results (required for .md file)
            if not final_result.get("__display__"):
                # Fallback: extract from other fields or create summary
                display_content = (
                    final_result.get("message") or 
                    final_result.get("ui_text") or 
                    final_result.get("text") or 
                    final_result.get("content") or
                    "✅ Dataset analysis completed. Full results saved to reports/analysis_output.md and reports/analyze_dataset_combined.md"
                )
                final_result["__display__"] = display_content
                logger.info(f"[analyze_dataset_tool] ✅ Ensured __display__ field contains results for .md file ({len(display_content)} chars)")
            
            # Add note about .md files being saved
            md_note = "\n\n📄 **Note:** Full analysis results have been saved to:\n"
            md_note += "- `reports/analysis_output.md` (formatted results)\n"
            md_note += "- `reports/analyze_dataset_combined.md` (detailed analysis)\n"
            md_note += "- `reports/full_analysis.json` (complete data)\n\n"
            
            # CRITICAL: Always generate and append menu - never skip it
            menu_text = ""
            menu_generated = False
            try:
                from .llm_menu_presenter import present_full_tool_menu
                logger.info(f"[analyze_dataset_tool] Attempting to generate menu with tool_context={tool_context is not None}")
                menu_result = present_full_tool_menu(tool_context)
                logger.info(f"[analyze_dataset_tool] Menu result: status={menu_result.get('status')}, has_menu={bool(menu_result.get('menu'))}")
                
                if menu_result.get("status") == "success" and menu_result.get("menu"):
                    menu_text = menu_result.get("menu", "")
                    menu_generated = True
                    logger.info(f"[analyze_dataset_tool] ✅ Successfully generated LLM menu ({len(menu_text)} chars)")
                else:
                    logger.warning(f"[analyze_dataset_tool] Menu generation returned: {menu_result}")
            except Exception as menu_err:
                logger.error(f"[analyze_dataset_tool] Menu generation failed: {menu_err}", exc_info=True)
            
            # FALLBACK: If LLM menu failed, generate a basic deterministic menu
            if not menu_generated or not menu_text:
                logger.info(f"[analyze_dataset_tool] Using fallback deterministic menu")
                menu_text = (
                    "## 📋 **Next Steps - Sequential Workflow Menu**\n\n"
                    "**Step 2: Data Cleaning & Preparation**\n"
                    "1. `robust_auto_clean_file()` - Comprehensive auto-cleaning with LLM insights\n"
                    "2. `impute_simple()` - Simple imputation (mean/median/mode)\n"
                    "3. `impute_knn()` - KNN-based imputation\n"
                    "4. `encode_data()` - Encode categorical variables\n"
                    "5. `scale_data()` - Scale numeric features\n\n"
                    "**Step 3: Exploratory Data Analysis**\n"
                    "6. `describe()` - Column-wise statistics\n"
                    "7. `plot()` - Visualizations (8 chart types)\n"
                    "8. `stats()` - AI-powered statistical analysis\n"
                    "9. `correlation_analysis()` - Correlation matrix\n\n"
                    "**Step 4: Feature Engineering**\n"
                    "10. `auto_feature_synthesis()` - Automated feature creation\n"
                    "11. `select_features()` - Feature selection\n"
                    "12. `apply_pca()` - Dimensionality reduction\n\n"
                    "**Step 5: Modeling**\n"
                    "13. `recommend_model()` - AI model recommendations\n"
                    "14. `train_classifier()` - Train classification model\n"
                    "15. `train_regressor()` - Train regression model\n"
                    "16. `smart_autogluon_automl()` - AutoML with AutoGluon\n\n"
                    "**Step 6: Evaluation & Reporting**\n"
                    "17. `evaluate()` - Model evaluation metrics\n"
                    "18. `explain_model()` - SHAP explanations\n"
                    "19. `export_executive_report()` - Generate executive PDF\n"
                )
            
            # CRITICAL: ALWAYS append menu to __display__ - never skip
            current_display = final_result.get("__display__", "")
            menu_section = md_note + f"\n\n{'='*60}\n\n"
            menu_section += "🚨🚨🚨 **MANDATORY - LLM MUST DISPLAY THIS MENU:**\n\n"
            menu_section += "## 📋 **SEQUENTIAL WORKFLOW MENU - NEXT STEPS**\n\n"
            menu_section += "**THIS MENU IS EMBEDDED IN THE __display__ FIELD - YOU MUST EXTRACT AND SHOW IT TO THE USER!**\n\n"
            menu_section += "The menu below shows all available tools organized by workflow stages. "
            menu_section += "Users need to see ALL options to choose their next action.\n\n"
            menu_section += f"{menu_text}\n\n"
            menu_section += "💡 **TIP:** Choose a tool from the numbered options above to proceed with the next stage of your data science workflow.\n"
            menu_section += "\n🚨 **REMINDER TO LLM:** This menu is part of the tool's output - NEVER skip displaying it!\n"
            
            final_result["__display__"] = current_display + menu_section
            final_result["message"] = final_result.get("__display__")
            final_result["ui_text"] = final_result.get("__display__")
            final_result["render_for_user"] = final_result.get("__display__")
            
            logger.info(f"[analyze_dataset_tool] ✅ Appended workflow menu to output (total __display__ length: {len(final_result.get('__display__', ''))} chars)")
            logger.info(f"[analyze_dataset_tool] Menu section length: {len(menu_section)} chars, Menu text length: {len(menu_text)} chars")
            
            # CRITICAL: Save JSON output to results/ folder for executive report
            # FIXED: Now saves even without tool_context using fallback paths
            try:
                from pathlib import Path
                import json
                from datetime import datetime
                import os
                
                # Try workspace first, fallback to current directory
                results_dir = None
                if tool_context:
                    state = getattr(tool_context, "state", {}) if hasattr(tool_context, "state") else {}
                    workspace_root = state.get("workspace_root") if isinstance(state, dict) else None
                    if workspace_root:
                        results_dir = Path(workspace_root) / "results"
                
                # Fallback: Use current directory or .uploaded/_workspaces/results
                if not results_dir:
                    # Try to find a workspace directory
                    from .large_data_config import UPLOAD_ROOT
                    possible_workspace = Path(UPLOAD_ROOT) / "_workspaces"
                    if possible_workspace.exists():
                        # Use the most recent workspace
                        workspaces = sorted([d for d in possible_workspace.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)
                        if workspaces:
                            results_dir = workspaces[0] / "results"
                
                # Final fallback: create results/ in current directory
                if not results_dir:
                    results_dir = Path("results")
                
                results_dir.mkdir(parents=True, exist_ok=True)
                output_file = results_dir / f"analyze_dataset_output_{int(datetime.now().timestamp())}.json"
                
                output_data = {
                    "tool_name": "analyze_dataset_tool",
                    "timestamp": datetime.now().isoformat(),
                    "status": final_result.get("status", "success"),
                    "display": final_result.get("__display__", ""),
                    "data": {
                        "shape": final_result.get("shape"),
                        "columns": final_result.get("columns"),
                        "numeric_features": final_result.get("numeric_features"),
                        "categorical_features": final_result.get("categorical_features"),
                        "head_preview": final_result.get("head_preview"),
                        "describe_summary": final_result.get("describe_summary"),
                    },
                    "artifacts": final_result.get("artifacts", []),
                    "metrics": final_result.get("metrics", {})
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, default=str)
                logger.info(f"[analyze_dataset_tool] ✅ Saved JSON output to results/ folder: {output_file}")
                # Also add to result so it's discoverable
                final_result.setdefault("artifacts", []).append(str(output_file))
            except Exception as json_err:
                logger.warning(f"[analyze_dataset_tool] Failed to save JSON to results/ folder: {json_err}", exc_info=True)
    
    # CRITICAL DEBUG: Log what we're returning
    logger.info(f"[analyze_dataset_tool] RETURNING result with __display__ length: {len(final_result.get('__display__', ''))} chars")
    logger.info(f"[analyze_dataset_tool] RETURNING result keys: {list(final_result.keys())}")
    logger.info(f"[analyze_dataset_tool] RETURNING __display__ preview: {final_result.get('__display__', '')[:200]}")
    
    # [FIX] ADK function responses need a simple, flat structure
    # Return ONLY the fields ADK expects - don't nest complex data
    # ADK will strip large nested data but preserve __display__
    adk_response = {
        "status": "success",
        "__display__": final_result.get("__display__", ""),
        "message": final_result.get("message", ""),
        "artifacts": final_result.get("artifacts", [])
    }
    
    logger.info(f"[analyze_dataset_tool] ADK response __display__ length: {len(adk_response['__display__'])} chars")
    return adk_response

def describe_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for describe."""
    import logging
    logger = logging.getLogger(__name__)
    
    from .ds_tools import describe
    import inspect
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    
    #  AUTO-BIND: If no csv_path provided, get from session state
    if not csv_path and tool_context and hasattr(tool_context, 'state'):
        csv_path = (tool_context.state.get("default_csv_path") or 
                   tool_context.state.get("dataset_csv_path") or "")
        if csv_path:
            logger.info(f"[describe_tool] Auto-bound csv_path from state: {csv_path}")
    
    # Support both async and sync implementations safely
    try:
        if inspect.iscoroutinefunction(describe):
            raw_result = _run_async(describe(csv_path=csv_path, tool_context=tool_context))
        else:
            raw_result = describe(csv_path=csv_path, tool_context=tool_context)
    except Exception as e:
        # Handle pandas ParserError and other file reading errors
        error_msg = str(e)
        if "ParserError" in str(type(e).__name__) or "Buffer overflow" in error_msg:
            error_msg = (
                f"File parsing error: {error_msg}\n\n"
                "**Possible causes:**\n"
                "- File is corrupted or malformed\n"
                "- File encoding issue (try re-saving as UTF-8)\n"
                "- File is too large for single read\n"
                "- Inconsistent column structure\n\n"
                "**Suggestions:**\n"
                "- Try `robust_auto_clean_file()` to fix the file\n"
                "- Check file encoding and delimiter\n"
                "- Verify file integrity"
            )
        logger.error(f"[describe_tool] Failed to read/analyze file: {e}", exc_info=True)
        return {
            "status": "error",
            "message": error_msg,
            "ui_text": error_msg.split('\n')[0],
            "__display__": error_msg,
            "error": str(e)
        }
    
    # DIAGNOSTIC: Log what describe() returned
    _log_tool_result_diagnostics(raw_result, "describe", "raw_tool_output")
    return _ensure_ui_display(raw_result, "describe", tool_context)

def correlation_analysis_tool(csv_path: str = "", method: str = "pearson", **kwargs) -> Dict[str, Any]:
    """
    ADK-safe wrapper for correlation analysis - find relationships between numeric features.
    
    Computes correlation matrix and identifies strong correlations to help with:
    - Feature selection
    - Multicollinearity detection
    - Relationship discovery
    
    Args:
        csv_path: Path to CSV file (optional, uses default from session)
        method: Correlation method - 'pearson', 'spearman', or 'kendall' (default: pearson)
    
    Returns:
        Dictionary with correlation matrix, strong correlations, and visualization
    
    Example:
        correlation_analysis_tool()  # Analyze correlations in active dataset
        correlation_analysis_tool(method="spearman")  # Use rank correlation
    """
    import pandas as pd
    import logging
    from pathlib import Path
    logger = logging.getLogger(__name__)
    
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")
    
    # Multi-layer validation
    from .file_validator import validate_file_multi_layer
    is_valid, result_or_error, metadata = validate_file_multi_layer(
        csv_path=csv_path,
        tool_context=tool_context,
        tool_name="correlation_analysis()",
        require_llm_validation=False
    )
    
    if not is_valid:
        logger.error(f"[correlation_analysis_tool] Validation FAILED")
        return {
            "status": "error",
            "message": result_or_error,
            "ui_text": result_or_error.split('\n')[0],
            "error": "validation_failed"
        }
    
    csv_path = result_or_error
    logger.info(f"[correlation_analysis_tool] Validation PASSED: {csv_path}")
    
    try:
        # Read data (CSV only)
        if csv_path.endswith('.parquet'):
            raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Select only numeric columns
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32']).columns.tolist()
        
        if len(numeric_cols) < 2:
            return {
                "status": "warning",
                "message": f"⚠️ **Not enough numeric columns for correlation analysis**\n\nFound {len(numeric_cols)} numeric column(s). Need at least 2.\n\n**Numeric columns:** {', '.join(numeric_cols) if numeric_cols else 'None'}",
                "__display__": f"⚠️ Not enough numeric columns ({len(numeric_cols)}). Need at least 2 for correlation analysis."
            }
        
        # Compute correlation matrix
        corr_matrix = df[numeric_cols].corr(method=method)
        
        # Find strong correlations (> 0.7 or < -0.7, excluding diagonal)
        strong_correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    strong_correlations.append({
                        "feature1": corr_matrix.columns[i],
                        "feature2": corr_matrix.columns[j],
                        "correlation": round(corr_val, 3)
                    })
        
        # Sort by absolute correlation value
        strong_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        
        # Format message
        message_parts = ["## 📊 Correlation Analysis Results\n"]
        message_parts.append(f"**Method:** {method.capitalize()}\n")
        message_parts.append(f"**Numeric Features:** {len(numeric_cols)}\n\n")
        
        if strong_correlations:
            message_parts.append(f"### 🔥 Strong Correlations Found: {len(strong_correlations)}\n")
            for i, item in enumerate(strong_correlations[:10], 1):
                emoji = "📈" if item["correlation"] > 0 else "📉"
                message_parts.append(f"{i}. {emoji} **{item['feature1']}** ↔ **{item['feature2']}**: {item['correlation']:.3f}\n")
            
            if len(strong_correlations) > 10:
                message_parts.append(f"\n_...and {len(strong_correlations) - 10} more_\n")
        else:
            message_parts.append("### ✅ No Strong Correlations\n")
            message_parts.append("No feature pairs with |correlation| > 0.7 found.\n")
        
        message_parts.append(f"\n**All Features:** {', '.join(numeric_cols[:10])}")
        if len(numeric_cols) > 10:
            message_parts.append(f" (+{len(numeric_cols) - 10} more)")
        
        formatted_message = "\n".join(message_parts)
        
        result = {
            "status": "success",
            "__display__": formatted_message,
            "message": formatted_message,
            "text": formatted_message,
            "ui_text": formatted_message,
            "content": formatted_message,
            "correlation_matrix": corr_matrix.to_dict(),
            "strong_correlations": strong_correlations,
            "numeric_features": numeric_cols,
            "method": method,
            "shape": df.shape
        }
        
        logger.info(f"[correlation_analysis_tool] Found {len(strong_correlations)} strong correlations")
        
    except Exception as e:
        logger.error(f"[correlation_analysis_tool] Failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"❌ **Correlation analysis failed**\n\nError: {str(e)}",
            "__display__": f"❌ Correlation analysis failed: {str(e)}",
            "error": str(e)
        }
    
    _log_tool_result_diagnostics(result, "correlation_analysis", "raw_tool_output")
    return _ensure_ui_display(result, "correlation_analysis", tool_context)


def shape_tool(csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """
    ADK-safe wrapper for shape - get dataset dimensions (rows × columns).
    
    Lightweight tool for quickly checking dataset size without loading full statistics.
    Perfect for verifying uploads, checking size before operations, and memory estimation.
    
    Uses multi-layer file validation to ensure file exists and is valid.
    
    Args:
        csv_path: Path to CSV file (optional, uses default from session)
    
    Returns:
        Dictionary with rows, columns, total cells, memory usage, and column names
    
    Example:
        shape_tool()  # Get dimensions of active dataset
    """
    from .ds_tools import shape
    from .file_validator import validate_file_multi_layer
    import logging
    logger = logging.getLogger(__name__)
    
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    
    #  MULTI-LAYER VALIDATION with LLM Intelligence
    is_valid, result_or_error, metadata = validate_file_multi_layer(
        csv_path=csv_path,
        tool_context=tool_context,
        tool_name="shape()",
        require_llm_validation=False
    )
    
    if not is_valid:
        # Validation failed - return _ensure_ui_display(detailed error message
        logger.error(f"[shape_tool] Multi-layer validation FAILED")
        return {
            "status": "error",
            "message": result_or_error,  # Contains detailed validation error
            "ui_text": result_or_error.split('\n')[0],  # First line for UI
            "error": "validation_failed",
            "rows": 0,
            "columns": 0
        }
    
    # Validation passed - use validated path
    csv_path = result_or_error  # This is now the validated, full file path
    logger.info(f"[shape_tool] Multi-layer validation PASSED - proceeding with: {csv_path}")
    
    result = shape(csv_path=csv_path, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "shape", "raw_tool_output")
    return _ensure_ui_display(result, "shape", tool_context)

# --- Head tool shim (to satisfy head_describe_guard import) ---
from typing import Optional

try:
    # Prefer a real implementation if it exists
    from .ds_tools import head as _head_impl

    def _head_inner_impl(*args, **kwargs):
        return _head_impl(*args, **kwargs)

except Exception:
    # Fallback: safe, ADK-friendly head() using session state
    def _head_inner_impl(tool_context: Optional['ToolContext'] = None, csv_path: str = "", n: int = 5):
        import os
        from glob import glob
        import pandas as pd
        from .large_data_config import UPLOAD_ROOT

        # Try explicit csv_path first, then session-provided path
        if not csv_path and tool_context and hasattr(tool_context, "state"):
            csv_path = tool_context.state.get("default_csv_path")

        # Fall back to newest upload
        if not csv_path:
            candidates = []
            for ext in ("*.csv",):
                candidates += glob(os.path.join(UPLOAD_ROOT, "**", ext), recursive=True)
            if candidates:
                csv_path = max(candidates, key=os.path.getmtime)

        if not csv_path:
            return {
                "status": "failed",
                "error": "No dataset found in session state or uploads. Upload a CSV file first."
            }

        # Load a small preview safely (CSV only)
        if csv_path.lower().endswith(".parquet"):
            raise ValueError(f"Parquet files are not supported. Only CSV files are accepted. Found: {csv_path}")
        # low-memory read of the first rows
        df = pd.read_csv(csv_path, nrows=max(n, 5))

        return {
            "status": "success",
            "shape": [int(df.shape[0]), int(df.shape[1])],
            "columns": list(map(str, df.columns)),
            "head": df.head(n).to_dict(orient="records"),
            "source": os.path.basename(csv_path),
        }

# Expose as a plain function (agent registers SafeFunctionTool around it)
def head_tool(n: int = 5, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    result = _head_inner_impl(tool_context=tool_context, csv_path=csv_path, n=n)
    _log_tool_result_diagnostics(result, "head", "raw_tool_output")
    return _ensure_ui_display(result, "head", tool_context)

async def plot_tool(csv_path: str = "", max_charts: int = 8, **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for plot (auto-plot).

    Note: The underlying plot function is async and expects (csv_path, max_charts, tool_context).
    This wrapper aligns with that signature and awaits the result.
    """
    from .ds_tools import plot
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("="*80)
    logger.info(f"[PLOT_TOOL] Called with csv_path={csv_path}, max_charts={max_charts}")
    
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    logger.info(f"[PLOT_TOOL] tool_context available: {tool_context is not None}")
    
    # Validate csv_path and fall back to default if file doesn't exist
    csv_arg = csv_path or None
    if csv_arg:
        # Check if the file exists; if not, try to find it in UPLOAD_ROOT
        if not os.path.exists(csv_arg):
            # Try to find it in UPLOAD_ROOT
            from .large_data_config import UPLOAD_ROOT
            from glob import glob
            # First try exact match in UPLOAD_ROOT
            candidate = os.path.join(UPLOAD_ROOT, csv_arg)
            if os.path.exists(candidate):
                csv_arg = candidate
                logger.info(f"Found file in UPLOAD_ROOT: {csv_arg}")
            else:
                # Search recursively for any file with this name
                candidates = glob(os.path.join(UPLOAD_ROOT, "**", csv_arg), recursive=True)
                if candidates:
                    csv_arg = candidates[0]
                    logger.info(f"Found file recursively: {csv_arg}")
                else:
                    # File not found, fall back to default from state
                    logger.warning(f"File not found: {csv_path}, falling back to default from state")
                    if tool_context and hasattr(tool_context, "state"):
                        csv_arg = tool_context.state.get("default_csv_path")
                        if csv_arg:
                            logger.info(f"Using default CSV from state: {csv_arg}")
                    if not csv_arg:
                        # Last resort: find newest CSV in UPLOAD_ROOT
                        all_csvs = glob(os.path.join(UPLOAD_ROOT, "**", "*.csv"), recursive=True)
                        # Parquet disabled - CSV only
                        if all_csvs:
                            csv_arg = max(all_csvs, key=os.path.getmtime)
                            logger.info(f"Using newest file in UPLOAD_ROOT: {csv_arg}")
                        else:
                            logger.error("No CSV files found in UPLOAD_ROOT")
                            return {"error": "No data file found", "status": "failed"}
    else:
        # No csv_path provided: try binding by state or newest in UPLOAD_ROOT
        if tool_context and hasattr(tool_context, "state"):
            csv_arg = tool_context.state.get("default_csv_path")
        if not csv_arg:
            from .large_data_config import UPLOAD_ROOT
            from glob import glob
            all_csvs = glob(os.path.join(UPLOAD_ROOT, "**", "*.csv"), recursive=True)
            # Parquet disabled - CSV only
            if all_csvs:
                csv_arg = max(all_csvs, key=os.path.getmtime)
                logger.info(f"Using newest file in UPLOAD_ROOT (no arg): {csv_arg}")
            else:
                logger.error("No CSV files found in UPLOAD_ROOT (no arg)")
                return {"error": "No data file found", "status": "failed"}
    
    logger.info(f"[PLOT_TOOL] Calling plot() with csv_path={csv_arg}")
    result = await plot(csv_path=csv_arg, max_charts=max_charts, tool_context=tool_context)
    logger.info(f"[PLOT_TOOL] plot() returned: {type(result)}, status={result.get('status') if isinstance(result, dict) else 'N/A'}")
    logger.info(f"[PLOT_TOOL] Artifacts in result: {len(result.get('artifacts', [])) if isinstance(result, dict) else 0}")
    logger.info("="*80)
    _log_tool_result_diagnostics(result, "plot", "raw_tool_output")
    # [CRITICAL FIX] Do NOT call _ensure_ui_display here - plot_tool_guard handles the display formatting
    # Calling _ensure_ui_display generates generic "Operation Complete" message before plot_tool_guard can add details
    return result  # Return raw result to let plot_tool_guard format it properly

def auto_analyze_and_model_tool(target: str, csv_path: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for auto_analyze_and_model."""
    from .ds_tools import auto_analyze_and_model
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    # auto_analyze_and_model is async, must use _run_async
    result = _run_async(auto_analyze_and_model(target=target, csv_path=csv_path, tool_context=tool_context))
    _log_tool_result_diagnostics(result, "auto_analyze_and_model", "raw_tool_output")
    return _ensure_ui_display(result, "auto_analyze_and_model", tool_context)

# ===== SKLEARN CAPABILITIES =====

def sklearn_capabilities_tool(**kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for sklearn_capabilities."""
    from .ds_tools import sklearn_capabilities
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    _log_tool_result_diagnostics(result, "sklearn_capabilities", "raw_tool_output")
    return _ensure_ui_display(sklearn_capabilities(tool_context=tool_context), "sklearn_capabilities", tool_context)

# ===== HELP =====

def list_tools_tool(category: str = "", **kwargs) -> Dict[str, Any]:
    """ADK-safe wrapper for list_tools - primary tool discovery command."""
    from .ds_tools import list_tools
    tool_context = kwargs.get("tool_context")
    
    # ===== CRITICAL: Setup artifact manager (enables artifact saving/loading) =====
    state = getattr(tool_context, "state", {}) if tool_context else {}
    try:
        from . import artifact_manager
        from .large_data_config import UPLOAD_ROOT
        try:
            artifact_manager.rehydrate_session_state(state)
        except Exception as e:
            logger.debug(f"[WORKSPACE] Could not rehydrate state: {e}")
        try:
            artifact_manager.ensure_workspace(state, UPLOAD_ROOT)
            logger.debug(f"[WORKSPACE] ✓ Workspace ready: {state.get('workspace_root', 'NOT SET')}")
        except Exception as e:
            logger.error(f"[WORKSPACE] ✗ Failed to create workspace: {e}")
    except Exception as e:
        logger.error(f"[TOOL WRAPPER] Unexpected error: {e}")

    cat = category or None
    result = list_tools(category=cat, tool_context=tool_context)
    _log_tool_result_diagnostics(result, "lists", "raw_tool_output")
    return _ensure_ui_display(result, "lists", tool_context)

def help_tool(command: str = "", csv_path: str = "", **kwargs) -> str:
    """ADK-safe wrapper for help (returns rich text)."""
    from .ds_tools import help as _help
    # Map arguments to ds_tools.help signature
    cmd = command or None
    csvp = csv_path or None
    return _help(command=cmd, csv_path=csvp)

# Validation disabled for now to avoid dictionary iteration issues
# TODO: Re-enable validation once server is stable
