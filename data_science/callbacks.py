"""
Agent callbacks for local, per-agent behavior.
Handles upload routing, state shaping, result normalization, and UI page publishing.
"""
from __future__ import annotations

import logging
import numpy as np
import json
import inspect
import csv
import io
import os
import mimetypes
import decimal
from typing import Dict, Any, List, Optional
from google.adk.agents.callback_context import CallbackContext

logger = logging.getLogger(__name__)

# Import UI sink and state store
try:
    from .ui_page import publish_ui_blocks
    from .state_store import save_ui_event, save_tool_execution, update_session
except Exception:
    from ui_page import publish_ui_blocks
    from state_store import save_ui_event, save_tool_execution, update_session

def _as_blocks(tool_name: str, result: dict):
    """
    Convert tool result to UI blocks.
    Heuristic: convert common fields to UI blocks.
    Tools can also return 'ui_blocks' directly to skip the heuristic.
    """
    logger.debug(f"[_as_blocks] Processing result for tool: {tool_name}")
    logger.debug(f"[_as_blocks] Result type: {type(result)}")
    if isinstance(result, dict):
        logger.debug(f"[_as_blocks] Result keys: {list(result.keys())}")
        logger.debug(f"[_as_blocks] __display__ present: {'__display__' in result}")
        if '__display__' in result:
            logger.debug(f"[_as_blocks] __display__ value: {str(result.get('__display__', 'MISSING'))[:200]}")
        logger.debug(f"[_as_blocks] message present: {'message' in result}")
        if 'message' in result:
            logger.debug(f"[_as_blocks] message value: {str(result.get('message', 'MISSING'))[:200]}")
    
    if not isinstance(result, dict):
        return [{"type": "markdown", "title": "Output", "content": str(result)}]
    
    # If tool explicitly provides ui_blocks, use them
    if "ui_blocks" in result and isinstance(result["ui_blocks"], list):
        return result["ui_blocks"]
    
    blocks = []
    
    # 🔥 CRITICAL FIX: If __display__ exists and has content, use it IMMEDIATELY
    # This ensures EDA tools (shape, stats, describe, etc.) show their formatted output
    # BUT: Filter out LLM-generated "NEXT STEPS" recommendations from tool output
    display_field = result.get("__display__") or result.get("display") or result.get("message") or result.get("ui_text") or result.get("text")
    if display_field and isinstance(display_field, str) and len(display_field.strip()) > 0:
        # CRITICAL: Remove LLM-generated "NEXT STEPS" sections from tool output
        # EXCEPTION: For analyze_dataset_tool, the menu is part of the legitimate tool output - NEVER filter it!
        # These should only be in LLM responses, not tool results
        # BUT: Only filter if it's clearly an LLM addition (not part of legitimate tool output)
        original_length = len(display_field)
        original_display = display_field
        
        # NEVER filter menu for analyze_dataset_tool - it's part of the tool's legitimate output
        is_analyze_dataset = "analyze_dataset" in tool_name.lower()
        has_menu = "SEQUENTIAL WORKFLOW MENU" in display_field or "MANDATORY - LLM MUST DISPLAY THIS MENU" in display_field
        
        # CRITICAL: For analyze_dataset_tool with menu, NEVER filter ANYTHING - preserve entire __display__
        if is_analyze_dataset and has_menu:
            logger.info(f"[_as_blocks] ✅ Preserving complete menu for analyze_dataset_tool ({len(display_field)} chars)")
            # Keep the entire display field - don't filter anything
        
        if not is_analyze_dataset and "[NEXT STEPS]" in display_field:
            # Split on NEXT STEPS marker and keep only the tool output part (before NEXT STEPS)
            parts = display_field.split("[NEXT STEPS]")
            if parts and parts[0] and len(parts[0].strip()) > 10:  # Only filter if there's substantial content before it
                display_field = parts[0].strip()
                logger.info(f"[_as_blocks] 🔧 Removed 'NEXT STEPS' section (was {original_length} chars, now {len(display_field)} chars)")
            else:
                # Not enough content before NEXT STEPS - might be legitimate, keep it
                display_field = original_display
        
        # Also remove any Stage references that might be at the end (like "**Stage 2: Data Cleaning")
        # These are LLM additions, not tool output
        # BUT: Only filter if Stage appears near the end, not in legitimate content
        if "**Stage" in display_field:
            # Check if Stage appears in the last 20% of the content (likely an addition)
            stage_pos = display_field.find("**Stage")
            if stage_pos > len(display_field) * 0.8:  # Only filter if Stage is in last 20%
                stage_parts = display_field.split("**Stage")
                if stage_parts and stage_parts[0] and len(stage_parts[0].strip()) > 10:
                    display_field = stage_parts[0].strip()
                    logger.info(f"[_as_blocks] 🔧 Removed 'Stage' section (was at position {stage_pos}/{len(original_display)})")
        
        if len(display_field.strip()) > 0:
            logger.info(f"[_as_blocks] ✅ FOUND DISPLAY CONTENT ({len(display_field)} chars), creating markdown block")
            logger.debug(f"[_as_blocks] Display content preview: {display_field[:300]}")
            # Ensure display fields are populated for downstream consumers
            result["__display__"] = display_field
            result["message"] = result.get("message") or display_field
            result["ui_text"] = result.get("ui_text") or display_field
            result["content"] = result.get("content") or display_field
            blocks.append({"type": "markdown", "title": "Summary", "content": display_field})
            logger.info(f"[_as_blocks] ✅ Created markdown block with {len(display_field)} chars of content")
        
        # Also add artifacts if present
        arts = result.get("artifacts") or result.get("artifact_names") or result.get("plots") or []
        if isinstance(arts, list) and arts:
            filenames = []
            for a in arts:
                if isinstance(a, dict):
                    filenames.append(a.get("name") or a.get("path") or str(a))
                else:
                    filenames.append(str(a))
            if filenames:
                blocks.append({"type": "artifact_list", "title": "Generated Artifacts", "files": filenames})
        
        logger.info(f"[_as_blocks] ✅ Returning {len(blocks)} blocks with display content")
        return blocks
    else:
        logger.warning(f"[_as_blocks] ⚠️ NO display content found, will try to extract from nested data...")
    
    # Extract text content (CHECK __display__ FIRST - highest priority!)
    txt = result.get("__display__") or result.get("display") or result.get("ui_text") or result.get("message") or result.get("content") or result.get("summary") or result.get("text") or result.get("_formatted_output")
    
    logger.info(f"[_as_blocks] Extracted txt type: {type(txt)}, length: {len(str(txt)) if txt else 0}, preview: {str(txt)[:150] if txt else None}")
    
    # CRITICAL: Check if txt is empty or just whitespace (even if _ensure_ui_display set it but it's empty)
    # Also check if txt is a generic message like "completed successfully" - if so, try to extract real data
    txt_is_empty = not txt or (isinstance(txt, str) and not txt.strip())
    txt_is_generic = False
    if isinstance(txt, str) and txt.strip():
        # Check for generic messages that indicate no real data was extracted
        generic_patterns = [
            "completed successfully",
            "operation completed",
            "tool completed",
            "status: success",
        ]
        txt_lower = txt.lower()
        # More aggressive: check if txt is mostly just these generic words
        txt_is_generic = any(pattern in txt_lower for pattern in generic_patterns) and len(txt.strip()) < 100
        # Also check if txt doesn't contain actual data indicators
        has_data_indicators = any(indicator in txt_lower for indicator in ['shape', 'rows', 'columns', 'mean', 'std', 'accuracy', 'r2', 'features'])
        if has_data_indicators:
            txt_is_generic = False  # Override - contains actual data
    
    # CRITICAL FIX: If no display text found OR it's empty/whitespace OR it's generic, extract from nested 'result' key
    if txt_is_empty or txt_is_generic:
        logger.info(f"[_as_blocks] Display text is {'empty' if txt_is_empty else 'generic'}, attempting to extract from nested 'result' key...")
        logger.info(f"[_as_blocks] Current txt: {txt[:100] if txt else None}")
        nested_result = result.get("result")
        logger.info(f"[_as_blocks] nested_result type: {type(nested_result)}, is_dict: {isinstance(nested_result, dict)}")
        if isinstance(nested_result, dict):
            logger.info(f"[_as_blocks] nested_result keys: {list(nested_result.keys())}")
        if nested_result and isinstance(nested_result, dict):
            # Build detailed message from nested result (same logic as _ensure_ui_display)
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
            
            # Extract metrics (can be at nested level or top level of nested_result)
            if "metrics" in nested_result:
                metrics = nested_result["metrics"]
                if isinstance(metrics, dict) and metrics:
                    data_parts.append(f"\n**📈 Metrics:**")
                    for key, value in list(metrics.items())[:10]:
                        if isinstance(value, (int, float)):
                            data_parts.append(f"  • **{key}**: {value:.4f}")
                        else:
                            data_parts.append(f"  • **{key}**: {value}")
            
            # Also check for top-level keys that might contain data (for tools that don't nest)
            # This handles tools that return flat structures like {'accuracy': 0.85, 'precision': 0.82, ...}
            top_level_data_keys = ['accuracy', 'precision', 'recall', 'f1', 'f1_score', 'roc_auc', 'r2', 'mae', 'mse', 'rmse']
            found_metrics = []
            for key in top_level_data_keys:
                if key in nested_result:
                    val = nested_result[key]
                    if isinstance(val, (int, float)):
                        found_metrics.append((key, val))
            
            if found_metrics and "metrics" not in nested_result:
                # Only add if we didn't already add metrics above
                data_parts.append(f"\n**📈 Metrics:**")
                for key, value in found_metrics[:10]:
                    data_parts.append(f"  • **{key}**: {value:.4f}")
            
            # Extract plots/artifacts
            plot_keys = ["artifacts", "plot_paths", "plots", "figure_paths"]
            plots_found = []
            for key in plot_keys:
                if key in nested_result:
                    val = nested_result[key]
                    if isinstance(val, list):
                        plots_found.extend([str(p) for p in val])
                    elif isinstance(val, str):
                        plots_found.append(val)
            
            if plots_found:
                data_parts.append(f"\n**📄 Generated Artifacts:**")
                for plot in plots_found[:20]:
                    plot_name = plot.split('/')[-1].split('\\')[-1]
                    data_parts.append(f"  • `{plot_name}`")
            
            # If no specific data extracted, try to extract ANY meaningful data from nested_result
            if not data_parts:
                # Look for any top-level keys that contain data
                meaningful_keys = ['summary', 'analysis', 'description', 'info', 'data', 'output', 'content']
                for key in meaningful_keys:
                    if key in nested_result:
                        val = nested_result[key]
                        if isinstance(val, str) and len(val.strip()) > 10:
                            data_parts.append(f"**{key.replace('_', ' ').title()}:** {val[:500]}")
                            break
                        elif isinstance(val, (dict, list)) and val:
                            import json
                            try:
                                data_parts.append(f"**{key.replace('_', ' ').title()}:** {json.dumps(val, indent=2, default=str)[:500]}")
                            except:
                                data_parts.append(f"**{key.replace('_', ' ').title()}:** {str(val)[:500]}")
                            break
            
            # If we successfully extracted data, use it
            if data_parts:
                # Determine header based on tool name or use generic
                if "analyze" in tool_name.lower() or "dataset" in tool_name.lower():
                    header = "📊 **Dataset Analysis Results**"
                elif "train" in tool_name.lower() or "model" in tool_name.lower():
                    header = "🤖 **Model Training Results**"
                elif "plot" in tool_name.lower() or "visual" in tool_name.lower():
                    header = "📈 **Visualization Results**"
                elif "describe" in tool_name.lower() or "summary" in tool_name.lower():
                    header = "📋 **Summary Statistics**"
                elif "correlation" in tool_name.lower():
                    header = "🔗 **Correlation Analysis**"
                else:
                    header = f"✅ **{tool_name.replace('_', ' ').title()} Results**"
                
                txt = f"{header}\n\n" + "\n".join(data_parts)
                logger.info(f"[_as_blocks] ✅ SUCCESS: Extracted {len(data_parts)} data parts from nested result, total length: {len(txt)} chars")
                logger.info(f"[_as_blocks] Preview: {txt[:200]}...")
                # Also set it in result for future use
                result["__display__"] = txt
                result["message"] = txt
                result["ui_text"] = txt
            else:
                logger.warning(f"[_as_blocks] ⚠️ No data parts extracted from nested_result (data_parts is empty)")
                logger.warning(f"[_as_blocks] nested_result keys available: {list(nested_result.keys()) if isinstance(nested_result, dict) else 'N/A'}")
                # Try to extract ANY data at all, even if it doesn't match our patterns
                if isinstance(nested_result, dict) and nested_result:
                    # Get first few key-value pairs as fallback
                    fallback_parts = []
                    for key, value in list(nested_result.items())[:5]:
                        if not key.startswith('_') and value is not None:
                            try:
                                if isinstance(value, (dict, list)):
                                    val_str = f"{type(value).__name__} with {len(value)} items"
                                else:
                                    val_str = str(value)[:200]
                                fallback_parts.append(f"**{key.replace('_', ' ').title()}:** {val_str}")
                            except:
                                pass
                    if fallback_parts:
                        fallback_txt = f"✅ **{tool_name.replace('_', ' ').title()} Results**\n\n" + "\n".join(fallback_parts)
                        txt = fallback_txt
                        result["__display__"] = txt
                        result["message"] = txt
                        result["ui_text"] = txt
                        logger.info(f"[_as_blocks] ✅ Used fallback extraction with {len(fallback_parts)} items")
    
    if txt:
        logger.info(f"[_as_blocks] ✅ Found display text, length: {len(str(txt))}, using it for UI")
        # Use the display text - this is what will appear in Session UI
        # Also merge back into result for consistency
        result["__display__"] = str(txt)
        result["message"] = result.get("message") or str(txt)
        result["ui_text"] = result.get("ui_text") or str(txt)
        result["content"] = result.get("content") or str(txt)
        blocks.append({"type": "markdown", "title": "Summary", "content": str(txt)})
    else:
        logger.warning(f"[_as_blocks] ❌ NO display text found in result - will use fallback!")
    
    # Simple table support if a CSV string or list-of-lists is returned
    rows = result.get("table_rows")
    if isinstance(rows, list) and rows:
        blocks.append({"type": "table", "title": "Data Table", "rows": rows})
    elif isinstance(result.get("table_csv"), str):
        try:
            rdr = list(csv.reader(io.StringIO(result["table_csv"])))
            if rdr:
                blocks.append({"type": "table", "title": "Data Table", "rows": rdr})
        except Exception:
            pass
    
    # Artifact list
    arts = result.get("artifacts") or result.get("artifact_names") or result.get("plots") or []
    if isinstance(arts, list) and arts:
        # Extract filenames from dicts or use strings directly
        filenames = []
        for a in arts:
            if isinstance(a, dict):
                filenames.append(a.get("name") or a.get("path") or str(a))
            else:
                filenames.append(str(a))
        if filenames:
            blocks.append({"type": "artifact_list", "title": "Generated Artifacts", "files": filenames})
    
    # Metrics/stats table
    if "metrics" in result and isinstance(result["metrics"], dict):
        rows = [["Metric", "Value"]]
        for k, v in result["metrics"].items():
            rows.append([str(k), str(v)])
        blocks.append({"type": "table", "title": "Metrics", "rows": rows})
    
    # If no blocks were created, add a default with MORE INFO
    if not blocks:
        logger.warning(f"[_as_blocks] No blocks created for {tool_name}! Creating fallback...")
        
        # Try to show SOMETHING useful from the result
        status = result.get("status", "completed")
        error = result.get("error")
        
        # Build a better fallback message
        fallback_parts = [f"**Tool:** `{tool_name}`"]
        fallback_parts.append(f"**Status:** {status}")
        
        if error:
            fallback_parts.append(f"**Error:** {error}")
        
        # Show available keys for debugging
        if result:
            fallback_parts.append(f"\n**Debug:** Result has keys: {', '.join(result.keys())}")
            
            # Try to show ANY non-empty field
            for key in ['overview', 'shape', 'rows', 'columns', 'data', 'head']:
                if key in result and result[key]:
                    fallback_parts.append(f"**{key.title()}:** {str(result[key])[:300]}")
                    break

            # Also surface nested 'result' content so the Markdown isn't empty
            try:
                nested = result.get("result")
                if isinstance(nested, dict) and nested:
                    # List nested keys and include a short pretty-printed JSON preview
                    nested_keys = ", ".join(list(nested.keys())[:10])
                    fallback_parts.append(f"**Nested Result Keys:** {nested_keys}")
                    import json as _json
                    preview = _json.dumps(nested, indent=2, default=str)
                    if len(preview) > 1000:
                        preview = preview[:1000] + "..."
                    fallback_parts.append(f"**Nested Result (preview):**\n\n```json\n{preview}\n```")
                elif isinstance(nested, (list, tuple)) and len(nested) > 0:
                    fallback_parts.append(f"**Nested Result (list length):** {len(nested)}")
                elif isinstance(nested, str) and nested.strip():
                    fallback_parts.append(f"**Nested Result (text):** {nested[:500]}")
            except Exception:
                pass
        
        fallback_content = "\n\n".join(fallback_parts)
        logger.debug(f"[_as_blocks] FALLBACK CONTENT: {fallback_content[:500]}")
        blocks.append({"type": "markdown", "title": "Result", "content": fallback_content})
    
    # Validate blocks before returning; add fallback if invalid/empty
    if not blocks or not isinstance(blocks, list) or not all(isinstance(b, dict) for b in blocks):
        logger.warning("[_as_blocks] Invalid or empty UI blocks, adding fallback")
        blocks = [{"type": "markdown", "title": "Result", "content": str(result)[:500]}]
    return blocks

async def force_publish_to_ui(
    callback_context,
    tool_name: str,
    result,
    *,
    tool_args=None,
) -> None:
    """
    Enforce result-to-UI publishing even if the ADK after_tool_callback never fires.
    - Normalizes result via _as_blocks
    - Publishes UI blocks
    - Persists an execution record under data_science/.uploaded/reports/tool_executions/
    """
    logger.debug(f"[force_publish_to_ui] tool_name: {tool_name}, result type: {type(result)}")
    if isinstance(result, dict):
        logger.debug(f"[force_publish_to_ui] result keys: {list(result.keys())}")
        logger.debug(f"[force_publish_to_ui] __display__: {result.get('__display__')[:200] if result.get('__display__') else None}")
    
    try:
        # Convert non-dict into dict for consistent handling
        if not isinstance(result, dict):
            result = {"status": "success", "__display__": str(result), "message": str(result)}

        # Build UI blocks (this also mirrors __display__/message/ui_text/content)
        logger.debug(f"[force_publish_to_ui] Calling _as_blocks for {tool_name}")
        blocks = _as_blocks(tool_name, result)
        logger.debug(f"[force_publish_to_ui] _as_blocks returned {len(blocks)} blocks")
        if not blocks or not isinstance(blocks, list) or not all(isinstance(b, dict) for b in blocks):
            blocks = [{"type": "markdown", "title": "Result", "content": str(result)[:1000]}]

        # Publish to the session UI page
        await publish_ui_blocks(callback_context, tool_name, blocks)

        # Persist execution record to the requested folder
        # data_science/.uploaded/reports/tool_executions/<tool>_<ts>.json
        from pathlib import Path
        from datetime import datetime
        base = Path(__file__).resolve().parent  # .../data_science
        outdir = base / ".uploaded" / "reports" / "tool_executions"
        outdir.mkdir(parents=True, exist_ok=True)
        outfile = outdir / f"{tool_name}_exec_{int(datetime.now().timestamp())}.json"
        payload = {
            "tool_name": tool_name,
            "timestamp": datetime.now().isoformat(),
            "args": tool_args or {},
            "result": result,
            "ui_blocks": blocks,
        }
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        logger.info(f"[force_publish_to_ui] wrote execution record: {outfile}")
    except Exception as e:
        logger.error(f"[force_publish_to_ui] failure: {e}", exc_info=True)

async def after_tool_callback(*, tool=None, tool_context=None, result=None, **kwargs):
    """
    Normalize tool results and store canonical state.
    
    Args:
        tool: The tool that was executed (has .name attribute)
        tool_context: ADK callback context
        result: Tool execution result
        **kwargs: Additional arguments (tool_args, etc.)
    """
    logger.debug(f"[after_tool_callback] Processing tool: {tool.name if tool else 'unknown'}")
    try:
        logger.debug(f"[force_publish_to_ui] RAW result type: {type(result)}")
        if isinstance(result, dict):
            logger.debug(f"[force_publish_to_ui] RAW result keys: {list(result.keys())}")
            if '__display__' in result:
                logger.debug(f"[force_publish_to_ui] RAW __display__ preview: {str(result.get('__display__', ''))[:200]}")
    except Exception as e:
        logger.debug(f"[after_tool_callback] Failed to log raw result: {e}")
    
    try:
        # Extract tool name and callback context; tolerate missing args
        tool_name = getattr(tool, 'name', str(tool)) if tool is not None else str(kwargs.get('tool_name', 'unknown'))
        callback_context = tool_context or kwargs.get('callback_context') or kwargs.get('tool_ctx')
        if callback_context is None:
            # Nothing to do if no context is provided
            return None
        
        # [OK] DEBUG: Log what we receive
        logger.info(f"[CALLBACK] Tool: {tool_name}")
        logger.info(f"[CALLBACK] Result type: {type(result)}")
        if isinstance(result, dict):
            logger.info(f"[CALLBACK] Result keys: {list(result.keys())}")
            logger.info(f"[CALLBACK] Has message: {'message' in result}")
            logger.info(f"[CALLBACK] Has ui_text: {'ui_text' in result}")
            logger.info(f"[CALLBACK] Has content: {'content' in result}")
            if 'message' in result:
                logger.info(f"[CALLBACK] Message preview: {str(result['message'])[:200]}")
        
        # ===== CRITICAL FIX: Handle ADK stripping result to null =====
        # If result is null but artifacts exist, load artifact content
        # CRITICAL: Only replace if result has NO meaningful content
        should_replace = result is None or (isinstance(result, dict) and result.get("result") is None and not any(result.get(key) for key in ["__display__", "message", "ui_text", "content", "text"]))
        
        if should_replace:
            logger.warning(f"[CALLBACK] Result has no meaningful content! Attempting to load from artifacts...")
            logger.info(f"[CALLBACK] Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            logger.info(f"[CALLBACK] Has __display__: {'__display__' in result if isinstance(result, dict) else False}")
            logger.info(f"[CALLBACK] Has message: {'message' in result if isinstance(result, dict) else False}")
            logger.info(f"[CALLBACK] Has ui_text: {'ui_text' in result if isinstance(result, dict) else False}")
            logger.info(f"[CALLBACK] Has content: {'content' in result if isinstance(result, dict) else False}")
            logger.info(f"[CALLBACK] Has text: {'text' in result if isinstance(result, dict) else False}")
        else:
            logger.info(f"[CALLBACK] Result has meaningful content, keeping as-is")
            if isinstance(result, dict):
                logger.info(f"[CALLBACK] Keeping result with keys: {list(result.keys())}")
                if "__display__" in result:
                    logger.info(f"[CALLBACK] __display__ length: {len(str(result['__display__']))}")
        
        if should_replace:
            try:
                state = getattr(callback_context, "state", {})
                workspace_root = state.get("workspace_root")
                if workspace_root:
                    from pathlib import Path
                    # Try to find tool output markdown
                    artifact_path = Path(workspace_root) / "reports" / f"{tool_name}_output.md"
                    if artifact_path.exists():
                        content = artifact_path.read_text(encoding="utf-8")
                        logger.info(f"[CALLBACK] ✓ Loaded {len(content)} chars from {artifact_path.name}")
                        result = {
                            "status": "success",
                            "__display__": content,
                            "message": content,
                            "ui_text": content[:500] + "..." if len(content) > 500 else content,
                            "content": content,
                            "loaded_from_artifact": str(artifact_path)
                        }
                    else:
                        logger.warning(f"[CALLBACK] Artifact not found: {artifact_path}")
            except Exception as e:
                logger.error(f"[CALLBACK] Failed to load artifact: {e}")
        
        # Ensure result is a dict for safe access
        if not isinstance(result, dict):
            result = {"status": "success", "result": result}
        # If result is still None (ADK may omit on streaming), default to success
        if result is None:
            result = {"status": "success"}
        
        # ===== ROUTE ARTIFACTS TO WORKSPACE =====
        try:
            from . import artifact_manager
            if hasattr(callback_context, "state"):
                artifact_manager.route_artifacts_from_result(callback_context.state, result, tool_name)
                logger.debug(f"[CALLBACK] Routed artifacts for {tool_name}")
        except Exception as e:
            logger.warning(f"[CALLBACK] Artifact routing failed for {tool_name}: {e}")
        
        # CRITICAL: For analyze_dataset_tool, store the menu in state so it can be displayed
        if "analyze_dataset" in tool_name.lower() and isinstance(result, dict):
            display_content = result.get("__display__") or result.get("message") or ""
            if "SEQUENTIAL WORKFLOW MENU" in display_content or "NEXT STEPS" in display_content:
                callback_context.state["pending_menu"] = display_content
                logger.info(f"[CALLBACK] ✅ Stored menu in state for {tool_name} ({len(display_content)} chars)")
        
        # Store canonical last result for chain steps
        callback_context.state["temp:last_result_kind"] = tool_name
        callback_context.state["temp:last_result_ok"] = result.get("status", "success") == "success"
        callback_context.state["temp:last_result_status"] = result.get("status", "success")
        
        # Helper to sanitize values for session state (must be deepcopy/picklable)
        def _safe(value):
            try:
                return json.loads(json.dumps(value, default=str))
            except Exception:
                try:
                    return str(value)
                except Exception:
                    return "[unavailable]"

        # Store tool-specific state based on result type
        if tool_name == "describe":
            # Extract shape information for policies
            if "shape" in result:
                shape = result["shape"]
                if isinstance(shape, (list, tuple)) and len(shape) >= 2:
                    callback_context.state["describe:rows"] = int(shape[0])
                    callback_context.state["describe:cols"] = int(shape[1])
            
            # Extract target information if available
            if "target" in result:
                callback_context.state["describe:target"] = result["target"]
            elif "target_column" in result:
                callback_context.state["describe:target"] = result["target_column"]
        
        elif tool_name in ["train_classifier", "train_regressor", "train"]:
            # Store model training results
            if "model" in result:
                callback_context.state["last_model"] = _safe(result["model"])  # avoid storing raw model object
            if "metrics" in result:
                callback_context.state["last_metrics"] = _safe(result["metrics"])
            if "accuracy" in result:
                callback_context.state["last_accuracy"] = _safe(result["accuracy"])
        
        elif tool_name == "ensemble":
            # Store ensemble results
            if "ensemble_metrics" in result:
                callback_context.state["last_ensemble_metrics"] = _safe(result["ensemble_metrics"])
            if "models_used" in result:
                callback_context.state["last_ensemble_models"] = _safe(result["models_used"])
        
        elif tool_name in ["impute_simple", "impute_knn", "impute_iterative"]:
            # Store imputation results
            if "imputed_columns" in result:
                callback_context.state["last_imputed_columns"] = _safe(result["imputed_columns"])
            if "imputation_methods" in result:
                callback_context.state["last_imputation_methods"] = _safe(result["imputation_methods"])
        
        # Store general success/failure state
        if result.get("status") == "success":
            callback_context.state["last_successful_tool"] = tool_name
        else:
            callback_context.state["last_failed_tool"] = tool_name
            callback_context.state["last_error"] = result.get("error", "Unknown error")
        
        logger.debug(f"[callback] Tool {tool_name} completed, state updated")
        
        # ============================================================================
        # SEQUENTIAL WORKFLOW: Append next stage menu after tool completion
        # ============================================================================
        try:
            # Get current workflow stage from state
            current_stage = callback_context.state.get("workflow_stage", 0)
            
            # Determine which stage this tool belongs to
            from .workflow_stages import get_stage_for_tool, get_next_stage, format_stage_menu
            tool_stage = get_stage_for_tool(tool_name)
            
            # Check for errors first - display error message prominently if tool failed
            has_error = False
            error_message = ""
            
            if isinstance(result, dict):
                # Check for error indicators
                tool_status = result.get("status", "").lower()
                error_field = result.get("__error__") or result.get("error")
                error_msg_field = result.get("error_message") or result.get("message", "")
                
                if tool_status in ("failed", "error") or error_field or (error_msg_field and "error" in error_msg_field.lower()):
                    has_error = True
                    # Extract concise error message
                    if isinstance(error_field, str):
                        error_message = error_field[:200]  # Limit length
                    elif error_msg_field and len(error_msg_field) > 0:
                        error_message = error_msg_field[:200]  # Limit length
                    else:
                        error_message = f"Tool {tool_name} encountered an error. Check logs for details."
            
            # If tool belongs to a recognized stage
            if tool_stage > 0:
                # Get stage info for status message
                try:
                    from .workflow_stages import get_stage
                    stage_info = get_stage(tool_stage)
                    stage_name = stage_info.get('name', f'Stage {tool_stage}') if stage_info else f'Stage {tool_stage}'
                    stage_icon = stage_info.get('icon', '📋') if stage_info else '📋'
                except:
                    stage_name = f'Stage {tool_stage}'
                    stage_icon = '📋'
                
                if has_error:
                    # ERROR CASE: Show error prominently, don't advance workflow
                    error_banner = (
                        "\n\n" + "=" * 60 + "\n"
                        "## ⚠️ **TOOL ERROR - DO NOT PROCEED**\n\n"
                        f"**Tool:** `{tool_name}`\n"
                        f"**Stage:** {tool_stage} - {stage_name}\n\n"
                        f"**Error:** {error_message}\n\n"
                        "**⚠️ IMPORTANT:** Please fix this error before proceeding to the next stage.\n"
                        "Review the error message above and try again or use a different tool.\n"
                        "=" * 60 + "\n\n"
                    )
                    
                    if isinstance(result, dict):
                        existing_display = result.get("__display__", "") or result.get("message", "") or ""
                        result["__display__"] = error_banner + existing_display
                        result["message"] = result["__display__"]
                        logger.warning(f"[WORKFLOW] ❌ {tool_name} FAILED - showing error banner, NOT advancing workflow")
                    
                    # Add stage status summary (FAILURE)
                    status_summary = (
                        "\n\n" + "-" * 60 + "\n"
                        f"## 📊 **STAGE {tool_stage} STATUS: ❌ FAILED**\n\n"
                        f"**Stage:** {stage_icon} {stage_name}\n"
                        f"**Tool:** `{tool_name}`\n"
                        f"**Result:** ❌ Failed - {error_message[:100]}{'...' if len(error_message) > 100 else ''}\n"
                        f"**Action Required:** Fix the error above before proceeding\n"
                        "-" * 60 + "\n"
                    )
                    
                    if isinstance(result, dict):
                        result["__display__"] = result.get("__display__", "") + status_summary
                        result["message"] = result["__display__"]
                
                elif result.get("status") == "success":
                    # SUCCESS CASE: Add status summary and advance to next stage
                    status_summary = (
                        "\n\n" + "-" * 60 + "\n"
                        f"## 📊 **STAGE {tool_stage} STATUS: ✅ COMPLETED**\n\n"
                        f"**Stage:** {stage_icon} {stage_name}\n"
                        f"**Tool:** `{tool_name}`\n"
                        f"**Result:** ✅ Successfully completed\n"
                        f"**Progress:** {tool_stage} of 14 stages completed\n"
                        "-" * 60 + "\n"
                    )
                    
                    next_stage_id = tool_stage + 1
                    
                    # Only advance if we haven't already shown this stage
                    # if next_stage_id > current_stage and next_stage_id <= 14:
                    #     # Get next stage menu
                    #     next_stage = get_next_stage(tool_stage)
                    #     stage_menu = format_stage_menu(next_stage)
                        
                    #     # Append status summary and next menu to result display
                    #     if isinstance(result, dict):
                    #         existing_display = result.get("__display__", "") or result.get("message", "") or ""
                    #         # Add status summary, then next stage menu
                    #         result["__display__"] = existing_display + status_summary + "\n\n" + "=" * 60 + "\n\n" + stage_menu
                    #         result["message"] = result["__display__"]  # Keep in sync
                            
                    #         # Update workflow stage in state
                    #         callback_context.state["workflow_stage"] = next_stage_id
                    #         logger.info(f"[WORKFLOW] ✅ Stage {tool_stage} ({stage_name}) COMPLETED → Advanced to Stage {next_stage_id}: {next_stage['name']}")
                    #     else:
                    #         logger.debug(f"[WORKFLOW] Result is not dict, cannot append menu")
                    # else:
                    #     # Still add status summary even if not advancing
                    #     if isinstance(result, dict):
                    #         existing_display = result.get("__display__", "") or result.get("message", "") or ""
                    #         result["__display__"] = existing_display + status_summary
                    #         result["message"] = result["__display__"]
                    #     logger.debug(f"[WORKFLOW] Stage {next_stage_id} already shown or complete")
                else:
                    # Unknown status - add neutral status summary
                    status_summary = (
                        "\n\n" + "-" * 60 + "\n"
                        f"## 📊 **STAGE {tool_stage} STATUS: ⚠️ UNKNOWN**\n\n"
                        f"**Stage:** {stage_icon} {stage_name}\n"
                        f"**Tool:** `{tool_name}`\n"
                        f"**Result:** ⚠️ Status: {result.get('status', 'unknown')}\n"
                        "-" * 60 + "\n"
                    )
                    
                    if isinstance(result, dict):
                        existing_display = result.get("__display__", "") or result.get("message", "") or ""
                        result["__display__"] = existing_display + status_summary
                        result["message"] = result["__display__"]
                    logger.debug(f"[WORKFLOW] Tool {tool_name} status is '{result.get('status')}' (not success/error)")
            else:
                logger.debug(f"[WORKFLOW] Tool {tool_name} not recognized for stage advancement (stage={tool_stage})")
        except Exception as e:
            logger.error(f"[WORKFLOW] Error advancing workflow stage: {e}", exc_info=True)
            # Don't fail the callback if workflow advancement fails
        
        # One-time artifact mirror for uploads so UI surfaces it reliably
        try:
            s = callback_context.state
            if s.get("default_csv_path") and not s.get("mirrored_upload_saved"):
                from google.genai import types as gen_types
                payload = f"file_id={s.get('default_corpus_id') or s.get('last_file_id','')}\npath={s['default_csv_path']}\n".encode("utf-8")
                part = gen_types.Part.from_bytes(data=payload, mime_type="text/plain")
                try:
                    await callback_context.save_artifact("last_upload.txt", part)
                except TypeError:
                    # Fallback if invoked from a sync path
                    import asyncio
                    import concurrent.futures
                    try:
                        loop = asyncio.get_running_loop()
                        # Loop is running - use thread executor
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(asyncio.run, callback_context.save_artifact("last_upload.txt", part))
                            future.result(timeout=10)
                    except RuntimeError:
                        # No loop - safe to use asyncio.run()
                        asyncio.run(callback_context.save_artifact("last_upload.txt", part))
                s["mirrored_upload_saved"] = True
        except Exception:
            pass
        
        # Block "success text" without artifacts for plot tools
        if result and isinstance(result, dict):
            has_artifacts = bool(result.get("artifacts")) or bool(result.get("plots"))
            if (result.get("status") == "success") and not has_artifacts and tool_name.lower().startswith("plot"):
                result["status"] = "failed"
                result["message"] = "Plot tool reported success but produced no artifacts."
        
        # [OK] Promote tool result text to the chat stream as an assistant message
        try:
            if isinstance(result, dict):
                ui_text = result.get("__display__") or result.get("ui_text") or result.get("message") or result.get("summary") or result.get("text") or result.get("display") or result.get("content")
                if ui_text and ui_text.strip():
                    # Log that we're trying to display this
                    logger.info(f"[CALLBACK] Promoting tool result to UI: {ui_text[:100]}...")
                    
                    # ADK approach: add an assistant message part to the conversation
                    # The callback_context should have access to add messages
                    try:
                        from google.genai import types as gen_types
                        # Create a text part with the tool result
                        text_part = gen_types.Part(text=ui_text[:4000])
                        # Try to append it as an assistant response
                        # Note: This depends on ADK version and runner implementation
                        if hasattr(callback_context, 'add_assistant_message'):
                            callback_context.add_assistant_message(text_part)
                            logger.info("[CALLBACK] [OK] Added assistant message via add_assistant_message")
                        elif hasattr(callback_context, 'reply'):
                            callback_context.reply(ui_text[:4000])
                            logger.info("[CALLBACK] [OK] Added assistant message via reply")
                        elif hasattr(callback_context, 'add_content'):
                            callback_context.add_content(text_part)
                            logger.info("[CALLBACK] [OK] Added assistant message via add_content")
                        else:
                            # Fallback: store in state for agent to potentially use
                            callback_context.state["_tool_result_to_display"] = ui_text[:4000]
                            logger.warning("[CALLBACK] [WARNING] No known method to add assistant message, stored in state")
                    except Exception as e:
                        logger.warning(f"[CALLBACK] Failed to add assistant message: {e}")
                        # Last resort: try setattr
                        setattr(callback_context, "reply_text", ui_text[:4000])
        except Exception as e:
            logger.error(f"[CALLBACK] Error promoting tool result: {e}", exc_info=True)
        
        # [OK] ARTIFACT ROUTING: Route any file paths to workspace and push to UI
        try:
            if isinstance(result, dict):
                # Collect artifact paths from common keys
                artifact_keys = [
                    "artifacts", "artifact_path", "plot_paths", "image_paths", "model_path",
                    "report_path", "output_path", "output_file", "paths", "files", "file_path"
                ]
                paths = []
                for k in artifact_keys:
                    v = result.get(k)
                    if not v:
                        continue
                    if isinstance(v, str):
                        paths.append(v)
                    elif isinstance(v, (list, tuple)):
                        paths.extend([x for x in v if isinstance(x, str)])
                    elif isinstance(v, dict):
                        paths.extend([x for x in v.values() if isinstance(x, str)])
                
                # De-dup paths
                seen = set()
                unique_paths = [p for p in paths if p and p not in seen and not seen.add(p)]
                
                # Push each artifact to UI
                saved_names = []
                for p in unique_paths:
                    try:
                        if not os.path.isfile(p):
                            continue
                        name = os.path.basename(p)
                        from google.genai import types
                        with open(p, "rb") as f:
                            data = f.read()
                        mime = mimetypes.guess_type(p)[0] or "application/octet-stream"
                        blob = types.Blob(data=data, mime_type=mime)
                        part = types.Part(inline_data=blob)
                        await callback_context.save_artifact(name, part)
                        saved_names.append(name)
                        logger.info(f"[CALLBACK] [OK] Pushed artifact to UI: {name}")
                    except Exception as e:
                        logger.warning(f"[CALLBACK] Failed to push artifact {p}: {e}")
                
                # Update result with artifact info
                if saved_names:
                    result["artifacts"] = saved_names
                    artifact_line = " • ".join(saved_names)
                    extra = f" Artifacts saved: {artifact_line}"
                    existing = result.get("__display__") or result.get("ui_text") or result.get("message") or ""
                    updated_text = (existing + ("\n" if existing else "") + extra).strip()
                    result["__display__"] = updated_text
                    result["ui_text"] = updated_text
                    result["message"] = updated_text
        except Exception as e:
            logger.error(f"[CALLBACK] Error in artifact routing: {e}", exc_info=True)
        
        #  UI SINK: Publish to session UI page and persist in SQLite
        try:
            import time
            start_time = time.time()
            
            # CRITICAL: Make a DEEP copy of result for _as_blocks to modify
            # This ensures _as_blocks can modify display fields without affecting downstream processing
            import copy
            result_for_ui = copy.deepcopy(result) if isinstance(result, dict) else {}
            if not isinstance(result_for_ui, dict) or not result_for_ui:
                # Ensure _as_blocks always has something usable
                result_for_ui = {"__display__": str(result) if result is not None else "No result available"}
            
            # Log what _as_blocks will receive
            logger.info(f"[CALLBACK] Before _as_blocks - result_for_ui keys: {list(result_for_ui.keys()) if isinstance(result_for_ui, dict) else 'N/A'}")
            if isinstance(result_for_ui, dict):
                logger.info(f"[CALLBACK] __display__ in result_for_ui: {'__display__' in result_for_ui}")
                if '__display__' in result_for_ui:
                    logger.info(f"[CALLBACK] __display__ value preview: {str(result_for_ui['__display__'])[:200]}")
            
            # Convert result to UI blocks (may modify result_for_ui to add __display__)
            blocks = _as_blocks(tool_name, result_for_ui)
            
            # Log what _as_blocks returned
            logger.info(f"[CALLBACK] After _as_blocks - blocks count: {len(blocks)}, block types: {[b.get('type') for b in blocks]}")
            
            # CRITICAL: Merge any display fields that _as_blocks extracted back into main result
            # This ensures the extracted data is preserved for clean_for_json and return
            if isinstance(result_for_ui, dict) and result_for_ui.get("__display__"):
                result["__display__"] = result_for_ui["__display__"]
                result["message"] = result_for_ui.get("message") or result_for_ui["__display__"]
                result["ui_text"] = result_for_ui.get("ui_text") or result_for_ui["__display__"]
                result["content"] = result_for_ui.get("content") or result_for_ui["__display__"]
                logger.info(f"[CALLBACK] ✓ Merged extracted display from _as_blocks back into result (length: {len(str(result['__display__']))})")
            
            # Publish to UI page (creates/updates session_ui_page.md in Artifacts)
            logger.info(f"[CALLBACK] About to call publish_ui_blocks for tool: {tool_name}")
            await publish_ui_blocks(callback_context, tool_name, blocks)
            logger.info(f"[CALLBACK] Completed publish_ui_blocks for tool: {tool_name}")
            
            # Persist in SQLite
            session_id = getattr(callback_context, "session_id", "default-session")
            save_ui_event(session_id, tool_name, blocks)
            
            # Track tool execution
            tool_args = kwargs.get("tool_args", {})
            success = result.get("status", "success") == "success" if isinstance(result, dict) else True
            duration_ms = (time.time() - start_time) * 1000
            save_tool_execution(session_id, tool_name, tool_args, result, success, duration_ms)
            
            # Update session activity
            update_session(session_id)
            
            logger.debug(f"[UI SINK] Published {len(blocks)} blocks for {tool_name}")
        except Exception as e:
            # Don't break the turn if UI publishing fails
            logger.warning(f"[UI SINK] Failed to publish UI blocks: {e}")
        
        # ===== SAVE ALL UI OUTPUTS TO WORKSPACE FOR REPORT INCLUSION =====
        try:
            # Save tool output as JSON in workspace for executive report
            if isinstance(result, dict) and result.get("__display__"):
                workspace_root = callback_context.state.get("workspace_root")
                
                # If workspace_root not set, try to ensure it exists
                if not workspace_root:
                    try:
                        from . import artifact_manager
                        from .large_data_config import UPLOAD_ROOT
                        artifact_manager.ensure_workspace(callback_context.state, UPLOAD_ROOT)
                        workspace_root = callback_context.state.get("workspace_root")
                        if workspace_root:
                            logger.info(f"[REPORT DATA] ✓ Created workspace for output saving: {workspace_root}")
                    except Exception as e:
                        logger.warning(f"[REPORT DATA] Could not create workspace: {e}")
                
                if workspace_root:
                    from pathlib import Path
                    import json
                    from datetime import datetime
                    
                    # Create results directory if it doesn't exist (NEW: dedicated results/ folder for structured outputs)
                    results_dir = Path(workspace_root) / "results"
                    results_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save output with timestamp
                    output_file = results_dir / f"{tool_name}_output_{int(datetime.now().timestamp())}.json"
                    
                    output_data = {
                        "tool_name": tool_name,
                        "timestamp": datetime.now().isoformat(),
                        "status": result.get("status", "success"),
                        "display": result.get("__display__"),
                        "data": result,
                        "artifacts": result.get("artifacts", []),
                        "metrics": result.get("metrics", {})
                    }
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, indent=2, default=str)
                    
                    logger.info(f"[REPORT DATA] ✓ Saved {tool_name} output: {output_file.name}")
                else:
                    logger.warning(f"[REPORT DATA] Cannot save {tool_name} output - workspace_root not available")
        except Exception as e:
            logger.error(f"[REPORT DATA] Failed to save tool output for report: {e}", exc_info=True)
        
        # ===== CRITICAL: Normalize result for UI display =====
        # Implement recommended sanitization functions for bullet-proof serialization
        import math
        
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
            """Recursively normalize nested structures to JSON-safe types."""
            if isinstance(obj, dict):
                return {str(k): normalize_nested(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [normalize_nested(v) for v in obj]
            return _to_py_scalar(obj)
        
        def clean_for_json(obj, depth=0):
            """Aggressively clean an object to ensure JSON serializability."""
            if depth > 10:  # Prevent infinite recursion
                return str(obj)
            
            # CRITICAL: Check for async generators, generators, coroutines FIRST
            if inspect.isasyncgen(obj) or inspect.isgenerator(obj) or inspect.iscoroutine(obj):
                return {"_type": "async_generator", "_info": "streaming"}
            
            # CRITICAL: Check numpy/pandas types FIRST (before native types)
            # because numpy.float64 is isinstance(float) but still needs conversion!
            obj_type = type(obj).__module__
            if obj_type == 'numpy' or obj_type.startswith('numpy.'):
                # Numpy scalar (int64, float64, etc.)
                if hasattr(obj, 'item') and hasattr(obj, 'ndim'):
                    try:
                        if obj.ndim == 0:  # 0-dimensional = scalar
                            return obj.item()
                    except:
                        pass
                # Numpy array or pandas types with tolist
                if hasattr(obj, 'tolist'):
                    try:
                        result = obj.tolist()
                        # Recursively clean the result (might contain more numpy types)
                        return clean_for_json(result, depth+1)
                    except:
                        pass
                # Fallback for other numpy types
                return str(obj)
            
            # Pandas types
            if obj_type.startswith('pandas.'):
                if hasattr(obj, 'tolist'):
                    try:
                        result = obj.tolist()
                        return clean_for_json(result, depth+1)
                    except:
                        pass
                if hasattr(obj, 'to_dict'):
                    try:
                        result = obj.to_dict()
                        return clean_for_json(result, depth+1)
                    except:
                        pass
                return str(obj)
            
            # Handle None, bool, str, int, float (natively serializable)
            # AFTER numpy/pandas check to avoid numpy.float64 passing through
            if obj is None or isinstance(obj, (bool, str, int, float)):
                return obj
            
            # Handle lists and tuples
            if isinstance(obj, (list, tuple)):
                try:
                    return [clean_for_json(item, depth+1) for item in obj]
                except:
                    return [str(item) for item in obj]
            
            # Handle dicts
            if isinstance(obj, dict):
                cleaned = {}
                for k, v in obj.items():
                    try:
                        cleaned[str(k)] = clean_for_json(v, depth+1)
                    except:
                        cleaned[str(k)] = str(v)
                return cleaned
            
            # Everything else: convert to string
            return str(obj)
        
        try:
            # CRITICAL: Detect and handle non-serializable types
            # These MUST be replaced, not allowed to flow through
            if inspect.isasyncgen(result) or inspect.isgenerator(result) or inspect.iscoroutine(result):
                logger.warning(f"[CALLBACK] Detected async_generator/generator/coroutine from {tool_name} - not supported")
                return {"status": "error", "message": f"{tool_name} returned unsupported async generator type. Use non-streaming version."}
            
            # Ensure result is a dict
            if not isinstance(result, dict):
                result = {"status": "success", "result": str(result)}
            
            # CRITICAL: Deep check for async generators inside the result dict
            def has_async_generator(obj, depth=0):
                """Recursively check for async generators in nested structures"""
                if depth > 5:  # Prevent infinite recursion
                    return False
                if inspect.isasyncgen(obj) or inspect.isgenerator(obj) or inspect.iscoroutine(obj):
                    return True
                if isinstance(obj, dict):
                    return any(has_async_generator(v, depth+1) for v in obj.values())
                if isinstance(obj, (list, tuple)):
                    return any(has_async_generator(item, depth+1) for item in obj)
                return False
            
            if has_async_generator(result):
                logger.warning(f"[CALLBACK] Found async_generator inside {tool_name} result - not supported")
                return {"status": "error", "message": f"{tool_name} returned unsupported async generator type. Use non-streaming version."}
            
            # CRITICAL: Clean the result FIRST to ensure JSON serializability
            result = clean_for_json(result)
            
            # CRITICAL: Ensure __display__ field exists and is populated
            if "__display__" not in result or not result["__display__"]:
                # Extract display text from various possible fields
                display_text = (
                    result.get("ui_text") or
                    result.get("message") or
                    result.get("text") or
                    result.get("content") or
                    result.get("display") or
                    result.get("_formatted_output") or
                    result.get("summary")
                )
                
                # If still no display text, build one from the result
                if not display_text:
                    status = result.get("status", "success")
                    if status == "success":
                        display_text = f"✅ **{tool_name}** completed successfully"
                        # Add artifacts if any
                        artifacts = result.get("artifacts") or result.get("artifact") or []
                        if artifacts:
                            if isinstance(artifacts, list):
                                display_text += f"\n\n**Artifacts:** {', '.join(str(a) for a in artifacts[:5])}"
                            else:
                                display_text += f"\n\n**Artifact:** {artifacts}"
                    else:
                        display_text = f"❌ **{tool_name}** completed with status: {status}"
                        error = result.get("error")
                        if error:
                            display_text += f"\n\n**Error:** {error}"
                
                # Set ALL display fields
                result["__display__"] = display_text
                result["message"] = display_text
                result["text"] = display_text
                result["ui_text"] = display_text
                result["content"] = display_text
                result["display"] = display_text
                result["_formatted_output"] = display_text
            
            # CRITICAL: We cleaned the result with clean_for_json above, which returns a NEW dict
            # We MUST return this cleaned result, not None!
            # Returning None would let the ORIGINAL (uncleaned) result flow through with async generators!
            
            # Check if result has the minimum required display fields
            has_display = any(result.get(f) for f in ["__display__", "message", "text", "ui_text"])
            
            if not has_display:
                # No display fields - this is unusual, add a basic one
                logger.warning(f"[CALLBACK] Result missing display fields, adding default")
                result["__display__"] = f"✅ **{tool_name}** completed"
                result["message"] = result.get("message") or f"{tool_name} completed successfully"
            
            logger.info(f"[CALLBACK] Returning cleaned result (has display: {has_display})")
            # CRITICAL: Return the cleaned result (with async generators removed)
            # Do NOT return None - that would use the original uncleaned result!
            return result
            
        except Exception as e:
            logger.error(f"[CALLBACK] Error in after_tool_callback: {e}", exc_info=True)
            # Return safe fallback - don't let potentially broken result through
            return {
                "status": "success",
                "__display__": f"✅ **{tool_name}** completed",
                "message": f"{tool_name} completed (callback error: {str(e)[:100]})",
                "callback_error": str(e)
            }
            
    except Exception as e:
        logger.warning(f"After-tool callback outer exception: {e}")
        # Return safe fallback for outer exceptions too
        return {
            "status": "success",
            "__display__": "✅ Tool completed",
            "message": "Tool completed successfully",
            "callback_error": str(e)
        }

def after_upload_callback_DISABLED(*, tool_context=None, result=None, **kwargs):
    """
    After a file is uploaded, set it as the default for subsequent tool calls.
    """
    logger.info("!!!!!!!!!!!!!!!!! after_upload_callback !!!!!!!!!!!!!!!!!")
    if result is None:
        logger.info("!!!!!!!!!!!!!!!!! after_upload_callback NO RESULT !!!!!!!!!!!!!!!!!")
        return

    # Set as default CSV
    # Your logic here to extract the file path from the result
    # For example, if result is a dict with a 'file_path' key:
    file_path = result.get("file_path")
    if file_path and tool_context:
        tool_context.state["default_csv_path"] = file_path
        logger.info(f"!!!!!!!!!!!!!!!!! Set default_csv_path to {file_path} !!!!!!!!!!!!!!!!!")

    # Trigger the bootstrap process that runs analyze_dataset
    try:
        from .llm_menu_presenter import _bootstrap_step1_and_menu
        # DISABLED: _bootstrap_step1_and_menu(tool_context)
        logger.info("!!!!!!!!!!!!!!!!! Triggered _bootstrap_step1_and_menu !!!!!!!!!!!!!!!!!")
    except Exception as e:
        logger.debug(f"[after_upload_callback] Failed to trigger _bootstrap_step1_and_menu: {e}")
