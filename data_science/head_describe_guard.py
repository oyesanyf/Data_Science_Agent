"""
Hardened head and describe tool guards to ensure outputs show in UI.

Uses multi-layer file validation system with LLM intelligence to ensure
files exist and are valid before processing.
"""
import logging
from pathlib import Path
from typing import Any, Dict
from .artifact_utils import sync_push_artifact, _exists
from .adk_safe_wrappers import head_tool as _head_inner, describe_tool as _describe_inner
from .file_validator import validate_file_multi_layer
from .utils.paths import ensure_workspace, resolve_csv, workspace_dir  # prefer workspace

logger = logging.getLogger(__name__)

def head_tool_guard(tool_context=None, **kwargs) -> Dict[str, Any]:
    """
    Wraps head_tool to ensure:
    - data preview is shown in chat
    - any generated files are pushed to Artifacts pane
    - user gets a friendly chat message
    """
    logger.debug(f"[HEAD GUARD] Starting head tool, kwargs keys: {list(kwargs.keys())}")
    
    #  MULTI-LAYER VALIDATION with LLM Intelligence
    csv_path = kwargs.get('csv_path', '')
    is_valid, result_or_error, metadata = validate_file_multi_layer(
        csv_path=csv_path,
        tool_context=tool_context,
        tool_name="head()",
        require_llm_validation=False  # Can enable for semantic validation
    )
    
    if not is_valid:
        # Validation failed - return detailed error message
        logger.warning(f"[HEAD GUARD] Multi-layer validation failed")
        return {
            "status": "error",
            "message": result_or_error,  # Contains detailed validation error
            "ui_text": result_or_error.split('\n')[0],  # First line for UI
            "error": "validation_failed"
        }
    
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
        logger.info(f"[HEAD GUARD] ✓ Artifact manager ensured workspace: {state.get('workspace_root')}")
    except Exception as e:
        logger.warning(f"[HEAD GUARD] ⚠ Failed to ensure workspace: {e}")
    
    # Validation passed - resolve via workspace as single source of truth
    try:
        ds_slug, ws, default_csv = ensure_workspace(result_or_error)
        resolved = resolve_csv(result_or_error or default_csv, dataset_slug=ds_slug)
        # CSV only
        csv_path = str(resolved)
    except Exception:
        # Fallback to validated path
        csv_path = result_or_error
    logger.info(f"[HEAD GUARD] Multi-layer validation passed, validated path: {csv_path}")
    if metadata:
        logger.debug(f"[HEAD GUARD] File metadata: {metadata.get('rows', '?')} rows × {metadata.get('columns', '?')} columns")
    
    #  CRITICAL: Pass the validated csv_path to the inner tool!
    kwargs['csv_path'] = csv_path
    logger.debug(f"[HEAD GUARD] Calling inner tool with csv_path: {csv_path}")
    
    result = _head_inner(tool_context=tool_context, **kwargs)
    logger.info(f"[HEAD GUARD] head_tool returned: {type(result)}, keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    if isinstance(result, dict):
        logger.info(f"[HEAD GUARD] Result status: {result.get('status')}")
        logger.info(f"[HEAD GUARD] Has head data: {'head' in result}")
        logger.info(f"[HEAD GUARD] Has shape: {'shape' in result}")
    
    if not isinstance(result, dict):
        result = {}

    # Format the actual data preview for display
    message_parts = [" **Data Preview (First Rows)**\n"]
    
    if "head" in result and result["head"]:
        import pandas as pd
        try:
            from .agent import sanitize_text
            df = pd.DataFrame(result["head"])
            
            # CRITICAL: Sanitize column names FIRST (this is where the junk comes from!)
            df.columns = [sanitize_text(str(col), ascii_only=True, max_len=120) for col in df.columns]
            
            # Create a sanitized copy of head data
            head_df = df.head(5).copy()
            
            # Sanitize all data values
            for col in head_df.columns:
                if pd.api.types.is_object_dtype(head_df[col]):
                    head_df[col] = head_df[col].astype(str).apply(
                        lambda x: sanitize_text(x, ascii_only=True, max_len=160) if pd.notna(x) and str(x) != 'nan' else "[empty]"
                    )
            
            # Generate markdown table with sanitized data
            try:
                table_md = head_df.to_markdown(index=False)
                # Final sanitization pass on the entire table markdown
                table_md = sanitize_text(table_md, ascii_only=True, max_len=2000)
            except Exception:
                # Fallback if to_markdown fails
                table_md = head_df.to_string(index=False)
                table_md = sanitize_text(table_md, ascii_only=True, max_len=2000)
            
            message_parts.append(f"```text\n{table_md}\n```")
        except Exception as e:
            logger.warning(f"[HEAD GUARD] Failed to format table: {e}")
            safe_preview = sanitize_text(str(result["head"])[:500], ascii_only=True)
            message_parts.append(f"```text\n{safe_preview}\n```")
    
    if "shape" in result:
        message_parts.append(f"\n**Shape:** {result['shape'][0]} rows × {result['shape'][1]} columns")
    
    if "columns" in result:
        from .agent import sanitize_text
        cols = result["columns"][:10]  # Show first 10 columns
        # CRITICAL: Sanitize column names before displaying
        sanitized_cols = [sanitize_text(str(col), ascii_only=True, max_len=120) for col in cols]
        message_parts.append(f"\n**Columns:** {', '.join(sanitized_cols)}")
        if len(result["columns"]) > 10:
            message_parts.append(f" (+{len(result['columns']) - 10} more)")
    
    formatted_message = "\n".join(message_parts)
    
    # [OK] CRITICAL: For ADK, make formatted message EXTREMELY prominent
    # The LLM must see and include this text in its response
    result_display = {
        "__display__": formatted_message,  # HIGHEST PRIORITY display field
        "text": formatted_message,
        "message": formatted_message,
        "ui_text": formatted_message,
        "content": formatted_message,
        "display": formatted_message,
        "_formatted_output": formatted_message,  # Extra redundancy
        "status": result.get("status", "success"),
        "head": result.get("head"),  # Keep original data too
        "shape": result.get("shape"),
        "columns": result.get("columns"),
        "artifacts": result.get("artifacts", [])
    }
    
    logger.debug(f"[HEAD GUARD] Formatted message length: {len(formatted_message)}")
    logger.debug(f"[HEAD GUARD] Message preview: {formatted_message[:200]}...")
    
    # Update result with display fields
    result.update(result_display)
    
    # ===== CRITICAL FIX: Save as markdown artifact (like plot() does with PNGs) =====
    # This is why plot() works - it saves files. We do the same with markdown.
    if tool_context and formatted_message:
        try:
            from pathlib import Path
            state = getattr(tool_context, "state", {})
            workspace_root = state.get("workspace_root")
            
            if workspace_root:
                # Save formatted output as markdown
                artifact_path = Path(workspace_root) / "reports" / "head_output.md"
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                
                markdown_content = f"""# Dataset Preview (First Rows)

{formatted_message}

---
*Generated by head() tool*
"""
                artifact_path.write_text(markdown_content, encoding="utf-8")
                logger.info(f"[HEAD GUARD] ✅ Saved markdown to: {artifact_path}")
                
                # Push to UI (like plot does)
                try:
                    sync_push_artifact(tool_context, str(artifact_path), display_name="head_output.md")
                    result["artifacts"] = result.get("artifacts", []) + [str(artifact_path)]
                    logger.info(f"[HEAD GUARD] ✅ Pushed head_output.md to UI")
                except Exception as e:
                    logger.warning(f"[HEAD GUARD] Failed to push artifact: {e}")
        except Exception as e:
            logger.warning(f"[HEAD GUARD] Failed to save markdown artifact: {e}")
    
    # If there are any artifacts, push them to UI
    state = getattr(tool_context, "state", {}) if tool_context else {}
    artifacts = result.get("artifacts", [])
    
    for artifact in artifacts:
        if isinstance(artifact, dict):
            path = artifact.get("path")
            if path and _exists(path) and tool_context and hasattr(tool_context, "save_artifact"):
                try:
                    sync_push_artifact(tool_context, path, display_name=Path(path).name)
                except Exception:
                    pass
    
    # Display guard: return instructive message if no data
    if not result.get("head") and not result.get("content") and not result.get("ui_text"):
        return {
            "status": "warning",
            "message": (
                " **The head tool did not return any data to display.**\n\n"
                "This may indicate:\n"
                "- Dataset is empty or not yet uploaded\n"
                "- File path not bound to session\n\n"
                "**Try:**\n"
                "1. `list_data_files()` - Check available files\n"
                "2. `analyze_dataset()` - Re-analyze and bind dataset\n"
                "3. Re-upload your CSV file\n\n"
                "(We auto-bind the latest upload as default_csv_path)"
            ),
            "ui_text": (
                " **The head tool did not return any data to display.**\n\n"
                "Try: `list_data_files()` → `analyze_dataset()` → `head()`"
            )
        }
    
    logger.debug(f"[HEAD GUARD] Returning result with keys: {list(result.keys())}")
    return result

def describe_tool_guard(tool_context=None, **kwargs) -> Dict[str, Any]:
    """
    Wraps describe_tool to ensure:
    - data summary is shown in chat
    - any generated files are pushed to Artifacts pane
    - user gets a friendly chat message
    """
    logger.debug(f"[DESCRIBE GUARD] Starting describe tool, kwargs keys: {list(kwargs.keys())}")
    
    #  MULTI-LAYER VALIDATION with LLM Intelligence
    csv_path = kwargs.get('csv_path', '')
    is_valid, result_or_error, metadata = validate_file_multi_layer(
        csv_path=csv_path,
        tool_context=tool_context,
        tool_name="describe()",
        require_llm_validation=False  # Can enable for semantic validation
    )
    
    if not is_valid:
        # Validation failed - return detailed error message
        logger.warning(f"[DESCRIBE GUARD] Multi-layer validation failed")
        return {
            "status": "error",
            "message": result_or_error,  # Contains detailed validation error
            "ui_text": result_or_error.split('\n')[0],  # First line for UI
            "error": "validation_failed"
        }
    
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
        logger.info(f"[DESCRIBE GUARD] ✓ Artifact manager ensured workspace: {state.get('workspace_root')}")
    except Exception as e:
        logger.warning(f"[DESCRIBE GUARD] ⚠ Failed to ensure workspace: {e}")
    
    # Validation passed - resolve via workspace as single source of truth
    try:
        ds_slug, ws, default_csv = ensure_workspace(result_or_error)
        resolved = resolve_csv(result_or_error or default_csv, dataset_slug=ds_slug)
        # CSV only
        csv_path = str(resolved)
    except Exception:
        # Fallback to validated path
        csv_path = result_or_error
    logger.info(f"[DESCRIBE GUARD] Multi-layer validation passed, validated path: {csv_path}")
    if metadata:
        logger.debug(f"[DESCRIBE GUARD] File metadata: {metadata.get('rows', '?')} rows × {metadata.get('columns', '?')} columns")
    
    #  CRITICAL: Pass the validated csv_path to the inner tool!
    kwargs['csv_path'] = csv_path
    logger.debug(f"[DESCRIBE GUARD] Calling inner tool with csv_path: {csv_path}")
    
    # Call inner tool; support both async and sync implementations
    # CRITICAL: Initialize result first to prevent NameError
    result = {"status": "error", "message": "Unknown error", "ui_text": "Unknown error"}
    try:
        import inspect
        import asyncio
        out = _describe_inner(tool_context=tool_context, **kwargs)
        if inspect.isawaitable(out):
            # Run the coroutine in an event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # nest_asyncio should allow this, but use run_until_complete as fallback
                    import nest_asyncio
                    nest_asyncio.apply()
                    result = loop.run_until_complete(out)
                else:
                    result = asyncio.run(out)
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(out)
        else:
            result = out
    except Exception as e:
        logger.error(f"[DESCRIBE GUARD] Inner describe failed: {e}", exc_info=True)
        # Ensure result is always a dict, even on error
        result = {"status": "error", "message": str(e), "ui_text": str(e), "__display__": f"Error: {str(e)}"}
    logger.info(f"[DESCRIBE GUARD] describe_tool returned: {type(result)}, keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    if isinstance(result, dict):
        logger.info(f"[DESCRIBE GUARD] Result status: {result.get('status')}")
        logger.info(f"[DESCRIBE GUARD] Has overview: {'overview' in result}")
        logger.info(f"[DESCRIBE GUARD] Has shape: {'shape' in result}")
    
    if not isinstance(result, dict):
        result = {}

    # Format the actual data summary for display
    message_parts = [" **Data Summary & Statistics**\n"]
    
    if "overview" in result:
        import json
        from .agent import sanitize_text
        try:
            overview = result["overview"]
            if isinstance(overview, str):
                overview = json.loads(overview)
            
            # CRITICAL: Sanitize column names in overview (keys are often column names)
            if isinstance(overview, dict):
                sanitized_overview = {}
                for key, value in overview.items():
                    # Sanitize the key (column name)
                    clean_key = sanitize_text(str(key), ascii_only=True, max_len=120)
                    # Sanitize string values
                    if isinstance(value, str):
                        clean_value = sanitize_text(value, ascii_only=True, max_len=200)
                    elif isinstance(value, dict):
                        # Recursively sanitize nested dicts
                        clean_value = {
                            sanitize_text(str(k), ascii_only=True, max_len=120): 
                            sanitize_text(str(v), ascii_only=True, max_len=200) if isinstance(v, str) else v
                            for k, v in value.items()
                        }
                    else:
                        clean_value = value
                    sanitized_overview[clean_key] = clean_value
                overview = sanitized_overview
            
            json_str = json.dumps(overview, indent=2)
            # Final sanitization pass on JSON string
            json_str = sanitize_text(json_str, ascii_only=True, max_len=3000)
            message_parts.append("```json")
            message_parts.append(json_str)
            message_parts.append("```")
        except Exception as e:
            logger.warning(f"[DESCRIBE GUARD] Failed to format overview: {e}")
            safe_overview = sanitize_text(str(result["overview"])[:1000], ascii_only=True)
            message_parts.append(f"```text\n{safe_overview}\n```")
    
    if "shape" in result:
        message_parts.append(f"\n**Dataset Shape:** {result['shape'][0]} rows × {result['shape'][1]} columns")
    
    if "columns" in result:
        message_parts.append(f"\n**Total Columns:** {len(result['columns'])}")
    
    if "numeric_features" in result:
        message_parts.append(f"\n**Numeric Features:** {len(result['numeric_features'])}")
    
    if "categorical_features" in result:
        message_parts.append(f"\n**Categorical Features:** {len(result['categorical_features'])}")
    
    formatted_message = "\n".join(message_parts)
    
    # CRITICAL: Final sanitization pass on the entire message
    from .agent import sanitize_text
    formatted_message = sanitize_text(formatted_message, ascii_only=False, max_len=3000)
    
    # [OK] CRITICAL: For ADK, make formatted message EXTREMELY prominent
    # The LLM must see and include this text in its response
    result_display = {
        "__display__": formatted_message,  # HIGHEST PRIORITY display field
        "text": formatted_message,
        "message": formatted_message,
        "ui_text": formatted_message,
        "content": formatted_message,
        "display": formatted_message,
        "_formatted_output": formatted_message,  # Extra redundancy
        "status": result.get("status", "success"),
        "overview": result.get("overview"),  # Keep original data too
        "shape": result.get("shape"),
        "columns": result.get("columns"),
        "numeric_features": result.get("numeric_features"),
        "categorical_features": result.get("categorical_features"),
        "missing_values": result.get("missing_values"),
        "artifacts": result.get("artifacts", [])
    }
    
    logger.debug(f"[DESCRIBE GUARD] Formatted message length: {len(formatted_message)}")
    logger.debug(f"[DESCRIBE GUARD] Message preview: {formatted_message[:200]}...")
    
    # Update result with display fields
    result.update(result_display)
    
    # ===== CRITICAL FIX: Save as markdown artifact (like plot() does with PNGs) =====
    # This is why plot() works - it saves files. We do the same with markdown.
    if tool_context and formatted_message:
        try:
            from pathlib import Path
            state = getattr(tool_context, "state", {})
            workspace_root = state.get("workspace_root")
            
            if workspace_root:
                # Save formatted output as markdown
                artifact_path = Path(workspace_root) / "reports" / "describe_output.md"
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                
                markdown_content = f"""# Dataset Statistical Summary

{formatted_message}

---
*Generated by describe() tool*
"""
                artifact_path.write_text(markdown_content, encoding="utf-8")
                logger.info(f"[DESCRIBE GUARD] ✅ Saved markdown to: {artifact_path}")
                
                # Push to UI (like plot does)
                try:
                    sync_push_artifact(tool_context, str(artifact_path), display_name="describe_output.md")
                    result["artifacts"] = result.get("artifacts", []) + [str(artifact_path)]
                    logger.info(f"[DESCRIBE GUARD] ✅ Pushed describe_output.md to UI")
                except Exception as e:
                    logger.warning(f"[DESCRIBE GUARD] Failed to push artifact: {e}")
        except Exception as e:
            logger.warning(f"[DESCRIBE GUARD] Failed to save markdown artifact: {e}")
    
    # If there are any artifacts, push them to UI
    state = getattr(tool_context, "state", {}) if tool_context else {}
    artifacts = result.get("artifacts", [])
    
    for artifact in artifacts:
        if isinstance(artifact, dict):
            path = artifact.get("path")
            if path and _exists(path) and tool_context and hasattr(tool_context, "save_artifact"):
                try:
                    sync_push_artifact(tool_context, path, display_name=Path(path).name)
                except Exception:
                    pass
    
    # Display guard: return instructive message if no data
    if not result.get("overview") and not result.get("shape") and not result.get("content") and not result.get("ui_text"):
        return {
            "status": "warning",
            "message": (
                " **The describe tool did not return any statistics.**\n\n"
                "This may indicate:\n"
                "- Dataset is empty or not yet uploaded\n"
                "- File path not bound to session\n\n"
                "**Try:**\n"
                "1. `list_data_files()` - Check available files\n"
                "2. `analyze_dataset()` - Re-analyze and bind dataset\n"
                "3. `ge_auto_profile()` - Validate schema and data quality\n\n"
                "(We auto-bind the latest upload as default_csv_path)"
            ),
            "ui_text": (
                " **The describe tool did not return any statistics.**\n\n"
                "Try: `list_data_files()` → `analyze_dataset()` → `describe()`"
            )
        }
    
    logger.debug(f"[DESCRIBE GUARD] Returning result with keys: {list(result.keys())}")
    return result
