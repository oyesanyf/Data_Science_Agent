"""
Universal guard wrappers for ALL EDA tools to ensure outputs show in UI.

This module wraps shape, stats, describe, head, correlation_analysis, and plot
to guarantee that their outputs are properly formatted and displayed in the UI.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Import async-safe artifact saving helper (like plot() uses)
try:
    from .utils.artifacts_io import save_path_as_artifact
    from .universal_async_sync_helper import async_sync_safe
except ImportError:
    # Fallback if imports fail
    async_sync_safe = lambda f: f
    save_path_as_artifact = None

def _format_eda_output(tool_name: str, result: Dict[str, Any]):
    """
    Universal formatter for EDA tool outputs.
    
    Extracts data from result and builds a rich, formatted display message.
    """
    if not isinstance(result, dict):
        return {
            "status": "error",
            "message": f"{tool_name} returned invalid result type",
            "__display__": f"❌ {tool_name} failed"
        }
    
    # If result already has a good __display__ field, use it
    existing_display = result.get("__display__", "")
    if existing_display and len(str(existing_display)) > 50:
        # Has substantial content, keep it
        return result
    
    # Build formatted message from result data
    parts = []
    
    # Shape information
    if "shape" in result:
        shape = result["shape"]
        if isinstance(shape, list) and len(shape) == 2:
            rows, cols = shape
            parts.append(f"📊 **Shape:** {rows:,} rows × {cols} columns")
    elif "rows" in result and "columns" in result:
        rows = result["rows"]
        cols = result["columns"]
        parts.append(f"📊 **Shape:** {rows:,} rows × {cols} columns")
    
    # Column information
    if "columns" in result or "column_names" in result:
        cols = result.get("columns") or result.get("column_names", [])
        if isinstance(cols, list) and cols:
            if len(cols) <= 10:
                parts.append(f"**Columns:** {', '.join(str(c) for c in cols)}")
            else:
                parts.append(f"**Columns ({len(cols)}):** {', '.join(str(c) for c in cols[:10])}... (+{len(cols)-10} more)")
    
    # Statistics/describe data
    if "statistics" in result or "stats" in result:
        stats = result.get("statistics") or result.get("stats", {})
        if isinstance(stats, dict) and stats:
            parts.append(f"\n**📈 Statistics:**")
            for col, col_stats in list(stats.items())[:5]:
                if isinstance(col_stats, dict):
                    mean = col_stats.get("mean")
                    std = col_stats.get("std")
                    if mean is not None and std is not None:
                        parts.append(f"  • **{col}**: mean={float(mean):.2f}, std={float(std):.2f}")
            if len(stats) > 5:
                parts.append(f"  *...and {len(stats) - 5} more columns*")
    
    # Head/preview data
    if "head" in result:
        head_data = result["head"]
        if head_data:
            import pandas as pd
            try:
                df = pd.DataFrame(head_data)
                table_md = df.head(5).to_markdown(index=False) if hasattr(df, 'to_markdown') else str(df.head(5))
                parts.append(f"\n**📋 Data Preview:**\n```\n{table_md}\n```")
            except Exception:
                parts.append(f"\n**📋 Data Preview:** {len(head_data)} rows")
    
    # Correlation data
    if "correlations" in result or "correlation_matrix" in result:
        corr = result.get("correlations") or result.get("correlation_matrix")
        if isinstance(corr, dict):
            strong = corr.get("strong", [])
            if strong:
                parts.append(f"\n**🔗 Strong Correlations ({len(strong)}):**")
                for pair in strong[:3]:
                    if isinstance(pair, dict):
                        col1 = pair.get("col1", "?")
                        col2 = pair.get("col2", "?")
                        val = pair.get("correlation", 0)
                        parts.append(f"  • {col1} ↔ {col2}: {float(val):.3f}")
                if len(strong) > 3:
                    parts.append(f"  *...and {len(strong) - 3} more*")
    
    # Artifacts
    artifacts = result.get("artifacts", [])
    if artifacts:
        parts.append(f"\n**📎 Artifacts:** {len(artifacts)} file(s) generated")
    
    # Build final message
    if parts:
        formatted_message = f"✅ **{tool_name.replace('_', ' ').title()} Complete**\n\n" + "\n".join(parts)
    else:
        # Fallback - use any existing message
        formatted_message = (result.get("message") or 
                           result.get("summary") or 
                           f"✅ {tool_name} completed successfully")
    
    # Update result with ALL display fields
    result["__display__"] = formatted_message
    result["text"] = formatted_message
    result["message"] = formatted_message
    result["ui_text"] = formatted_message
    result["content"] = formatted_message
    result["display"] = formatted_message
    result["_formatted_output"] = formatted_message
    
    logger.info(f"[EDA GUARD] Formatted {tool_name} output ({len(formatted_message)} chars)")
    
    return result


@async_sync_safe
async def shape_tool_guard(csv_path: str = "", tool_context: Optional[Any] = None, **kwargs):
    """Guard wrapper for shape_tool using universal pattern (like plot_tool_guard)."""
    from .adk_safe_wrappers import shape_tool
    from .universal_tool_guard import universal_tool_guard
    
    def _save_markdown_artifact(tc, display_text: str):
        """Save markdown artifact and return path."""
        from pathlib import Path
        state = getattr(tc, "state", {}) if tc else {}
        workspace_root = state.get("workspace_root")
        if workspace_root and display_text:
            artifact_path = Path(workspace_root) / "reports" / "shape_output.md"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_content = f"""# Dataset Shape Analysis

{display_text}

---
*Generated by shape() tool*
"""
            artifact_path.write_text(markdown_content, encoding="utf-8")
            return str(artifact_path)
        return None
    
    # Call inner tool and format output
    result = shape_tool(csv_path=csv_path, tool_context=tool_context, **kwargs)
    result = _format_eda_output("shape", result)
    
    # Save markdown artifact if we have display content
    if tool_context and result.get("__display__"):
        artifact_path = _save_markdown_artifact(tool_context, result.get("__display__", ""))
        if artifact_path:
            # Add to result artifacts list so universal guard picks it up
            result.setdefault("artifacts", []).append(artifact_path)
    
    # Use universal guard pattern (like plot_tool_guard)
    # Note: universal_tool_guard automatically adds navigation reminders
    return await universal_tool_guard(
        tool_name="shape",
        inner_tool=lambda **k: result,  # Already called, just return result
        artifact_type="report",
        artifact_dir="reports",
        artifact_extension=".md",
        tool_context=tool_context,
        kwargs={},
        result_artifact_keys=["artifacts", "files"],
    )


@async_sync_safe
async def stats_tool_guard(csv_path: str = "", tool_context: Optional[Any] = None, **kwargs):
    """Guard wrapper for stats_tool using universal pattern (like plot_tool_guard)."""
    from .adk_safe_wrappers import stats_tool
    from .universal_tool_guard import universal_tool_guard
    
    def _save_markdown_artifact(tc, display_text: str):
        """Save markdown artifact and return path."""
        from pathlib import Path
        state = getattr(tc, "state", {}) if tc else {}
        workspace_root = state.get("workspace_root")
        if workspace_root and display_text:
            artifact_path = Path(workspace_root) / "reports" / "stats_output.md"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_content = f"""# AI-Powered Statistical Analysis

{display_text}

---
*Generated by stats() tool*
"""
            artifact_path.write_text(markdown_content, encoding="utf-8")
            return str(artifact_path)
        return None
    
    # Call inner tool and format output
    result = stats_tool(csv_path=csv_path, tool_context=tool_context, **kwargs)
    result = _format_eda_output("stats", result)
    
    # Save markdown artifact if we have display content
    if tool_context and result.get("__display__"):
        artifact_path = _save_markdown_artifact(tool_context, result.get("__display__", ""))
        if artifact_path:
            result.setdefault("artifacts", []).append(artifact_path)
    
    # Use universal guard pattern
    return await universal_tool_guard(
        tool_name="stats",
        inner_tool=lambda **k: result,
        artifact_type="report",
        artifact_dir="reports",
        artifact_extension=".md",
        tool_context=tool_context,
        kwargs={},
        result_artifact_keys=["artifacts", "files"],
    )


@async_sync_safe
async def correlation_analysis_tool_guard(csv_path: str = "", tool_context: Optional[Any] = None, **kwargs):
    """Guard wrapper for correlation_analysis_tool using universal pattern (like plot_tool_guard)."""
    from .adk_safe_wrappers import correlation_analysis_tool
    from .universal_tool_guard import universal_tool_guard
    
    def _save_markdown_artifact(tc, display_text: str):
        """Save markdown artifact and return path."""
        from pathlib import Path
        state = getattr(tc, "state", {}) if tc else {}
        workspace_root = state.get("workspace_root")
        if workspace_root and display_text:
            artifact_path = Path(workspace_root) / "reports" / "correlation_analysis_output.md"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_content = f"""# Correlation Analysis

{display_text}

---
*Generated by correlation_analysis() tool*
"""
            artifact_path.write_text(markdown_content, encoding="utf-8")
            return str(artifact_path)
        return None
    
    # Call inner tool and format output
    result = correlation_analysis_tool(csv_path=csv_path, tool_context=tool_context, **kwargs)
    result = _format_eda_output("correlation_analysis", result)
    
    # Save markdown artifact if we have display content
    if tool_context and result.get("__display__"):
        artifact_path = _save_markdown_artifact(tool_context, result.get("__display__", ""))
        if artifact_path:
            result.setdefault("artifacts", []).append(artifact_path)
    
    # Use universal guard pattern
    return await universal_tool_guard(
        tool_name="correlation_analysis",
        inner_tool=lambda **k: result,
        artifact_type="report",
        artifact_dir="reports",
        artifact_extension=".md",
        tool_context=tool_context,
        kwargs={},
        result_artifact_keys=["artifacts", "files"],
    )

