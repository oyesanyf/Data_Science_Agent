"""
Universal Artifact Generator
============================

Ensures EVERY tool generates a markdown artifact that is saved via ADK Artifact Manager.
This system NEVER fails - even if artifact saving has issues, the tool result is preserved.

Key Features:
- Automatic markdown generation from ANY tool result
- ADK-compliant artifact saving via ToolContext
- Fail-safe error handling (never crashes the tool)
- LLM-enhanced markdown formatting
- Comprehensive logging
- Artifact versioning support
"""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)

# Tools logger for artifact operations
try:
    from .logging_config import get_tools_logger
    tools_logger = get_tools_logger()
except ImportError:
    tools_logger = logger  # Fallback to default logger

# Import ADK types
try:
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    logger.warning("[ARTIFACT GEN] google.genai not available, using fallback")
    GENAI_AVAILABLE = False


class UniversalArtifactGenerator:
    """
    Universal artifact generator that ensures every tool creates a markdown artifact.
    
    Features:
    - Converts any tool result to markdown
    - Saves via ADK artifact manager (ToolContext)
    - Never fails (comprehensive error handling)
    - LLM-enhanced formatting (optional)
    - Automatic filename generation
    """
    
    def __init__(self, use_llm_formatting: bool = False):
        """
        Initialize artifact generator.
        
        Args:
            use_llm_formatting: Whether to use LLM for enhanced markdown formatting
        """
        self.use_llm_formatting = use_llm_formatting
        self.artifacts_generated = 0
        self.artifacts_failed = 0
    
    def generate_artifact_name(self, tool_name: str, result: Any) -> str:
        """
        Generate artifact filename from tool name and result.
        
        Args:
            tool_name: Name of the tool that generated the result
            result: Tool result (any type)
            
        Returns:
            Artifact filename (e.g., "analyze_dataset_output.md")
        """
        # Clean tool name
        clean_name = tool_name.replace("_tool", "").replace("__", "_").strip("_")
        
        # Check if result has a specific artifact name
        if isinstance(result, dict):
            if "artifact_name" in result:
                return result["artifact_name"]
            if "artifact_filename" in result:
                return result["artifact_filename"]
        
        # Generate default name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{clean_name}_output.md"
    
    def convert_to_markdown(self, result: Any, tool_name: str) -> str:
        """
        Convert any tool result to markdown format.
        AGGRESSIVELY extracts ALL data from results, including nested structures.
        
        Args:
            result: Tool result (dict, string, list, etc.)
            tool_name: Name of the tool
            
        Returns:
            Markdown-formatted string with ALL results
        """
        try:
            markdown_lines = []
            
            # Header
            markdown_lines.append(f"# {tool_name.replace('_', ' ').title()} Output")
            markdown_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            markdown_lines.append(f"**Tool:** `{tool_name}`\n")
            
            # CRITICAL: Handle plot/visualization tools specially
            if 'plot' in tool_name.lower() or ('artifacts' in str(result) and any(ext in str(result) for ext in ['.png', '.jpg', '.svg'])):
                markdown_lines.append(self._handle_plot_result(result))
            
            # CRITICAL: Unwrap nested results RECURSIVELY
            # Many tools wrap results in {'status': 'success', 'result': {...}}
            elif isinstance(result, dict):
                # Check for nested result - extract it fully
                if 'result' in result and isinstance(result['result'], (dict, list, str)):
                    nested_result = result['result']
                    
                    # Show status first if present
                    if 'status' in result:
                        status = result['status']
                        emoji = "✅" if status == "success" else "⚠️" if status == "warning" else "❌"
                        markdown_lines.append(f"\n**Status:** {emoji} {status}\n")
                    
                    # Now extract the ACTUAL nested result data
                    markdown_lines.append("## Results\n")
                    
                    if isinstance(nested_result, dict):
                        # Recursively extract ALL data from nested dict
                        markdown_lines.append(self._dict_to_markdown(nested_result))
                    elif isinstance(nested_result, str):
                        markdown_lines.append(nested_result + "\n")
                    elif isinstance(nested_result, (list, tuple)):
                        for i, item in enumerate(nested_result, 1):
                            markdown_lines.append(f"### Item {i}\n")
                            if isinstance(item, dict):
                                markdown_lines.append(self._dict_to_markdown(item))
                            else:
                                markdown_lines.append(str(item) + "\n")
                    else:
                        markdown_lines.append(f"```\n{str(nested_result)}\n```\n")
                    
                    # Also include any other metadata
                    for key in ['message', 'error', 'warning']:
                        if key in result and key not in ['result', 'status']:
                            markdown_lines.append(f"\n**{key.replace('_', ' ').title()}:** {result[key]}\n")
                
                # Check for metrics (common in model evaluation)
                elif 'metrics' in result:
                    markdown_lines.append("## Metrics\n")
                    metrics = result['metrics']
                    if isinstance(metrics, dict):
                        markdown_lines.append(self._dict_to_markdown(metrics))
                    else:
                        markdown_lines.append(f"{metrics}\n")
                
                # Standard dict processing with aggressive extraction
                else:
                    markdown_lines.append("## Results\n")
                    markdown_lines.append(self._dict_to_markdown(result))
            
            elif isinstance(result, str):
                markdown_lines.append("## Output\n")
                markdown_lines.append(result)
            
            elif isinstance(result, (list, tuple)):
                markdown_lines.append("## Output Items\n")
                for i, item in enumerate(result, 1):
                    markdown_lines.append(f"### Item {i}\n")
                    if isinstance(item, dict):
                        markdown_lines.append(self._dict_to_markdown(item))
                    else:
                        markdown_lines.append(str(item))
                    markdown_lines.append("\n")
            
            else:
                markdown_lines.append("## Output\n")
                markdown_lines.append(f"```\n{str(result)}\n```\n")
            
            # Footer
            markdown_lines.append("\n---")
            markdown_lines.append(f"\n*Generated by {tool_name} via Universal Artifact Generator*")
            
            return "\n".join(markdown_lines)
        
        except Exception as e:
            logger.error(f"[ARTIFACT GEN] Error converting to markdown: {e}")
            # Fallback: simple string conversion
            return f"# {tool_name} Output\n\n```\n{str(result)}\n```"
    
    def _handle_plot_result(self, result: Any) -> str:
        """
        Special handler for plot/visualization tool results.
        Extracts plot file paths and creates a summary with embedded image references.
        
        Args:
            result: Plot tool result
            
        Returns:
            Markdown string with plot summary and image references
        """
        markdown_lines = []
        
        markdown_lines.append("## Visualization Output\n")
        
        # Extract plot file paths from various possible locations
        plot_paths = []
        if isinstance(result, dict):
            # Check common keys for plot paths
            for key in ['artifacts', 'plot_paths', 'plots', 'figure_paths', 'saved_files']:
                if key in result:
                    value = result[key]
                    if isinstance(value, list):
                        plot_paths.extend([str(p) for p in value if p])
                    elif value:
                        plot_paths.append(str(value))
            
            # Add status and summary info
            if 'status' in result:
                markdown_lines.append(f"**Status:** {result['status']}\n")
            
            if 'charts' in result:
                charts = result['charts']
                if isinstance(charts, list) and charts:
                    markdown_lines.append(f"\n**Charts Generated:** {len(charts)}\n")
                    for i, chart in enumerate(charts, 1):
                        if isinstance(chart, dict):
                            chart_type = chart.get('type', 'unknown')
                            columns = chart.get('columns', [])
                            markdown_lines.append(f"{i}. **{chart_type}**: {', '.join(map(str, columns[:5]))}")
                            if len(columns) > 5:
                                markdown_lines.append(f" (+{len(columns)-5} more)")
                            markdown_lines.append("\n")
            
            if 'rows' in result and 'cols' in result:
                markdown_lines.append(f"\n**Dataset Shape:** {result['rows']} rows × {result['cols']} columns\n")
        
        # List generated plots
        if plot_paths:
            markdown_lines.append(f"\n### Generated Plot Files ({len(plot_paths)})\n")
            for i, plot_path in enumerate(plot_paths, 1):
                from pathlib import Path
                filename = Path(plot_path).name
                markdown_lines.append(f"{i}. `{filename}`")
                
                # Add image reference if it's a supported format
                if any(plot_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.svg']):
                    # Use relative path for markdown image embedding
                    markdown_lines.append(f"\n   ![Plot {i}]({filename})\n")
                else:
                    markdown_lines.append("\n")
        else:
            markdown_lines.append("\n⚠️ No plot files were generated.\n")
        
        # Add any additional info from __display__ field
        if isinstance(result, dict) and '__display__' in result:
            display_text = result['__display__']
            if display_text and str(display_text).strip():
                markdown_lines.append(f"\n### Summary\n\n{display_text}\n")
        
        return "\n".join(markdown_lines)
    
    def _dict_to_markdown(self, data: Dict, level: int = 2) -> str:
        """Convert dictionary to markdown format with AGGRESSIVE data extraction."""
        lines = []
        
        # Track which keys we've already processed
        processed_keys = set()
        
        # Handle special keys first
        if "status" in data:
            status = data["status"]
            emoji = "✅" if status == "success" else "⚠️" if status == "warning" else "❌"
            lines.append(f"**Status:** {emoji} {status}\n")
            processed_keys.add("status")
        
        # Priority keys that contain important data - extract these FIRST
        priority_keys = [
            "overview", "summary", "analysis", "description", 
            "shape", "rows", "cols", "columns", "dtypes",
            "data", "values", "items", "records",
            "missing", "missing_values", "nulls",
            "statistics", "stats", "describe"
        ]
        
        for priority_key in priority_keys:
            if priority_key in data and priority_key not in processed_keys:
                value = data[priority_key]
                header = "#" * level
                clean_key = priority_key.replace("_", " ").title()
                
                if isinstance(value, dict):
                    lines.append(f"{header} {clean_key}\n")
                    lines.append(self._dict_to_markdown(value, level + 1))
                elif isinstance(value, (list, tuple)):
                    lines.append(f"{header} {clean_key}\n")
                    if value and len(value) > 0 and isinstance(value[0], dict):
                        # Table format for list of dicts
                        lines.append(self._list_of_dicts_to_table(value))
                    else:
                        for item in value:
                            lines.append(f"- {item}")
                        lines.append("\n")
                elif isinstance(value, str) and len(value) > 100:
                    lines.append(f"{header} {clean_key}\n")
                    lines.append(f"{value}\n")
                else:
                    lines.append(f"**{clean_key}:** {value}\n")
                
                processed_keys.add(priority_key)
        
        # Special handling for metrics (training results)
        if "metrics" in data and isinstance(data["metrics"], dict):
            lines.append("## Model Performance Metrics\n")
            metrics = data["metrics"]
            
            # Common metrics with clear labels
            metric_order = [
                ("accuracy", "Accuracy"),
                ("test_acc", "Test Accuracy"),
                ("precision", "Precision"),
                ("recall", "Recall"),
                ("f1", "F1 Score"),
                ("f1_macro", "F1 Macro"),
                ("r2", "R²"),
                ("r_squared", "R²"),
                ("mae", "MAE"),
                ("mse", "MSE"),
                ("rmse", "RMSE"),
                ("auc", "AUC"),
                ("roc_auc", "ROC AUC"),
            ]
            
            for key, label in metric_order:
                if key in metrics:
                    value = metrics[key]
                    if isinstance(value, (int, float)):
                        lines.append(f"**{label}:** {value:.4f}")
                    else:
                        lines.append(f"**{label}:** {value}")
            
            # Add any other metrics not in the standard list
            for key, value in metrics.items():
                if key not in [m[0] for m in metric_order]:
                    clean_key = key.replace("_", " ").title()
                    if isinstance(value, (int, float)):
                        lines.append(f"**{clean_key}:** {value:.4f}")
                    else:
                        lines.append(f"**{clean_key}:** {value}")
            
            lines.append("\n")
            processed_keys.add("metrics")
        
        if "__display__" in data and isinstance(data["__display__"], str):
            lines.append("## Summary\n")
            lines.append(data["__display__"])
            lines.append("\n")
            processed_keys.add("__display__")
        
        # Process ALL remaining keys (aggressive extraction)
        for key, value in data.items():
            if key in processed_keys:
                continue
            
            header = "#" * level
            clean_key = key.replace("_", " ").title()
            
            if isinstance(value, dict):
                lines.append(f"{header} {clean_key}\n")
                lines.append(self._dict_to_markdown(value, level + 1))
            
            elif isinstance(value, (list, tuple)):
                lines.append(f"{header} {clean_key}\n")
                if value and isinstance(value[0], dict):
                    # Table format for list of dicts
                    lines.append(self._list_of_dicts_to_table(value))
                else:
                    for item in value:
                        lines.append(f"- {item}")
                    lines.append("\n")
            
            elif isinstance(value, str) and len(value) > 100:
                lines.append(f"{header} {clean_key}\n")
                lines.append(f"{value}\n")
            
            else:
                lines.append(f"**{clean_key}:** {value}\n")
        
        return "\n".join(lines)
    
    def _list_of_dicts_to_table(self, items: list) -> str:
        """Convert list of dictionaries to markdown table."""
        if not items:
            return ""
        
        try:
            # Get all unique keys
            keys = set()
            for item in items:
                if isinstance(item, dict):
                    keys.update(item.keys())
            
            keys = sorted(keys)
            
            # Header
            lines = []
            lines.append("| " + " | ".join(str(k).replace("_", " ").title() for k in keys) + " |")
            lines.append("| " + " | ".join(["---"] * len(keys)) + " |")
            
            # Rows
            for item in items:
                if isinstance(item, dict):
                    row = []
                    for key in keys:
                        value = item.get(key, "")
                        # Truncate long values
                        value_str = str(value)[:50]
                        if len(str(value)) > 50:
                            value_str += "..."
                        row.append(value_str)
                    lines.append("| " + " | ".join(row) + " |")
            
            lines.append("\n")
            return "\n".join(lines)
        
        except Exception as e:
            logger.warning(f"[ARTIFACT GEN] Could not create table: {e}")
            return "\n".join([f"- {item}" for item in items]) + "\n"
    
    def save_artifact_via_context(
        self,
        tool_context: Any,
        markdown_content: str,
        artifact_name: str
    ) -> bool:
        """
        Save artifact using ADK ToolContext artifact manager (ADK-compliant).
        
        Per ADK documentation:
        - Artifacts must be google.genai.types.Part with inline_data
        - Call await context.save_artifact(filename, artifact_part)
        - Returns version number
        
        Args:
            tool_context: ADK ToolContext (with save_artifact method)
            markdown_content: Markdown content to save
            artifact_name: Filename for the artifact
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if tool_context has artifact capabilities
            if not hasattr(tool_context, 'save_artifact'):
                logger.warning(f"[ARTIFACT GEN] ToolContext missing save_artifact method")
                return False
            
            # Create artifact Part per ADK spec
            if GENAI_AVAILABLE:
                # Convert string to bytes for inline_data
                markdown_bytes = markdown_content.encode('utf-8')
                
                # Create Part with Blob (ADK-compliant way)
                artifact_part = types.Part(
                    inline_data=types.Blob(
                        data=markdown_bytes,
                        mime_type="text/markdown"
                    )
                )
                
                # Alternative: Use convenience method
                # artifact_part = types.Part.from_bytes(
                #     data=markdown_bytes,
                #     mime_type="text/markdown"
                # )
            else:
                logger.error(f"[ARTIFACT GEN] google.genai not available - cannot create ADK-compliant artifact")
                return False
            
            # Save via ToolContext (could be sync or async)
            import asyncio
            import inspect
            import concurrent.futures
            
            # Check if save_artifact is async
            if inspect.iscoroutinefunction(tool_context.save_artifact):
                # Async save_artifact - need to handle event loop properly
                try:
                    # Try to get current event loop
                    try:
                        loop = asyncio.get_running_loop()
                        loop_is_running = True
                    except RuntimeError:
                        loop = None
                        loop_is_running = False
                    
                    if loop_is_running:
                        # CRITICAL FIX: We're in a running event loop
                        # Cannot use asyncio.run() or run_until_complete()
                        # Must run in separate thread
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(
                                asyncio.run,
                                tool_context.save_artifact(artifact_name, artifact_part)
                            )
                            version = future.result(timeout=30)  # 30 second timeout
                        tools_logger.info(f"[ARTIFACT] ✅ Saved '{artifact_name}' to ADK service (version {version}) via async thread")
                        logger.info(f"[ARTIFACT GEN] ✓ Saved artifact '{artifact_name}' (version {version}) via thread")
                        self.artifacts_generated += 1
                        return True
                    else:
                        # No running loop - safe to use asyncio.run()
                        version = asyncio.run(
                            tool_context.save_artifact(artifact_name, artifact_part)
                        )
                        tools_logger.info(f"[ARTIFACT] ✅ Saved '{artifact_name}' to ADK service (version {version})")
                        logger.info(f"[ARTIFACT GEN] ✓ Saved artifact '{artifact_name}' (version {version})")
                        self.artifacts_generated += 1
                        return True
                except Exception as e:
                    tools_logger.error(f"[ARTIFACT] ✗ Async save failed for '{artifact_name}': {e}")
                    logger.error(f"[ARTIFACT GEN] Async save failed for '{artifact_name}': {e}")
                    self.artifacts_failed += 1
                    return False
            else:
                # Synchronous save_artifact
                version = tool_context.save_artifact(artifact_name, artifact_part)
                tools_logger.info(f"[ARTIFACT] ✅ Saved '{artifact_name}' to ADK service (version {version})")
                logger.info(f"[ARTIFACT GEN] ✓ Saved artifact '{artifact_name}' (version {version})")
                self.artifacts_generated += 1
                return True
        
        except ValueError as e:
            # Per ADK docs: ValueError if artifact_service not configured
            logger.error(f"[ARTIFACT GEN] ValueError saving '{artifact_name}': {e}")
            logger.error("[ARTIFACT GEN] Is ArtifactService configured in Runner?")
            self.artifacts_failed += 1
            return False
        
        except Exception as e:
            logger.error(f"[ARTIFACT GEN] Failed to save artifact '{artifact_name}': {e}")
            logger.debug(traceback.format_exc())
            self.artifacts_failed += 1
            return False
    
    def save_artifact_to_workspace(
        self,
        markdown_content: str,
        artifact_name: str,
        workspace_root: Optional[str] = None
    ) -> bool:
        """
        Fallback: Save artifact directly to workspace filesystem.
        Used when ToolContext artifact manager is not available.
        
        Args:
            markdown_content: Markdown content to save
            artifact_name: Filename for the artifact
            workspace_root: Workspace root directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not workspace_root:
                logger.warning("[ARTIFACT GEN] No workspace_root provided for fallback save")
                return False
            
            # Create artifacts directory
            artifacts_dir = Path(workspace_root) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            tools_logger.info(f"[ARTIFACT] Created/verified artifact folder: {artifacts_dir}")
            
            # Save file
            artifact_path = artifacts_dir / artifact_name
            with open(artifact_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            file_size = artifact_path.stat().st_size
            tools_logger.info(f"[ARTIFACT] ✅ Saved artifact '{artifact_name}' to workspace folder '{artifacts_dir}' ({file_size} bytes)")
            logger.info(f"[ARTIFACT GEN] ✓ Saved artifact to filesystem: {artifact_path}")
            self.artifacts_generated += 1
            return True
        
        except Exception as e:
            logger.error(f"[ARTIFACT GEN] Failed to save artifact to filesystem: {e}")
            self.artifacts_failed += 1
            return False
    
    def ensure_artifact_generated(
        self,
        tool_name: str,
        result: Any,
        tool_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Ensure an artifact is generated for the tool result.
        This is the main entry point - NEVER fails.
        
        Args:
            tool_name: Name of the tool
            result: Tool result (any format)
            tool_context: ADK ToolContext (optional)
            
        Returns:
            Updated result with artifact information added
        """
        try:
            # CRITICAL: Validate result has actual data before creating artifact
            try:
                from .result_validation import validate_tool_result
                has_results, warning_msg = validate_tool_result(tool_name, result, throw_exception=False)
                if not has_results:
                    tools_logger.error(
                        f"[ARTIFACT] ⚠ Creating artifact for tool '{tool_name}' but result has no visible data. "
                        f"This will create an empty/minimal artifact."
                    )
            except Exception as validation_error:
                tools_logger.warning(f"[ARTIFACT] Validation check failed for {tool_name}: {validation_error}")
            
            # Generate artifact name
            artifact_name = self.generate_artifact_name(tool_name, result)
            
            # Ensure .md extension
            if not artifact_name.endswith('.md'):
                artifact_name += '.md'
            
            # Convert to markdown (AGGRESSIVE extraction)
            markdown_content = self.convert_to_markdown(result, tool_name)
            
            # CRITICAL: Ensure markdown has content - if empty or too short, extract more
            if len(markdown_content.strip()) < 100:
                logger.warning(f"[ARTIFACT GEN] Markdown too short for {tool_name}, extracting more aggressively")
                # Try to extract from __display__, message, overview, etc.
                if isinstance(result, dict):
                    additional_content = []
                    for key in ['__display__', 'message', 'overview', 'text', 'content', 'ui_text', 'display']:
                        if key in result and result[key]:
                            additional_content.append(f"## {key.replace('_', ' ').title()}\n\n{result[key]}\n")
                    
                    if additional_content:
                        markdown_content += "\n\n" + "\n".join(additional_content)
            
            # CRITICAL: Validate markdown has substantial content
            if len(markdown_content.strip()) < 50:
                # Fallback: create basic markdown with whatever we have
                markdown_content = f"""# {tool_name.replace('_', ' ').title()} Output

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Tool:** `{tool_name}`

## Result

{json.dumps(result, indent=2, default=str)[:2000]}

---
*This artifact was auto-generated. Result data is included above.*
"""
                logger.warning(f"[ARTIFACT GEN] Used fallback markdown for {tool_name}")
            
            # Try to save via ToolContext first
            saved_via_context = False
            if tool_context:
                saved_via_context = self.save_artifact_via_context(
                    tool_context, markdown_content, artifact_name
                )
            
            # Fallback: Save to workspace filesystem
            if not saved_via_context and tool_context and hasattr(tool_context, 'state'):
                workspace_root = tool_context.state.get('workspace_root')
                if workspace_root:
                    self.save_artifact_to_workspace(
                        markdown_content, artifact_name, workspace_root
                    )
            
            # Add artifact info to result (if dict)
            if isinstance(result, dict):
                result["artifact_generated"] = artifact_name
                result["artifact_status"] = "saved"
                
                # Add to artifacts list if not present
                if "artifacts" not in result:
                    result["artifacts"] = []
                if artifact_name not in result["artifacts"]:
                    result["artifacts"].append(artifact_name)
            
            tools_logger.info(f"[ARTIFACT] ✅ Successfully generated and saved artifact '{artifact_name}' for tool '{tool_name}'")
            logger.info(f"[ARTIFACT GEN] ✓ Generated artifact for {tool_name}: {artifact_name}")
            
        except Exception as e:
            tools_logger.error(f"[ARTIFACT] ✗ Critical error generating artifact for tool '{tool_name}': {e}")
            logger.error(f"[ARTIFACT GEN] ✗ Critical error generating artifact for {tool_name}: {e}")
            logger.debug(traceback.format_exc())
            self.artifacts_failed += 1
            
            # Add failure info to result (if dict)
            if isinstance(result, dict):
                result["artifact_status"] = "failed"
                result["artifact_error"] = str(e)
        
        return result
    
    def get_stats(self) -> Dict[str, int]:
        """Get artifact generation statistics."""
        return {
            "generated": self.artifacts_generated,
            "failed": self.artifacts_failed,
            "success_rate": (
                self.artifacts_generated / (self.artifacts_generated + self.artifacts_failed) * 100
                if (self.artifacts_generated + self.artifacts_failed) > 0
                else 100.0
            )
        }


# Global instance
_artifact_generator = UniversalArtifactGenerator()


def ensure_artifact_for_tool(
    tool_name: str,
    result: Any,
    tool_context: Optional[Any] = None
) -> Any:
    """
    Convenience function to ensure artifact generation for any tool.
    
    This function NEVER fails - it will always return the result,
    with or without successful artifact generation.
    
    Args:
        tool_name: Name of the tool
        result: Tool result
        tool_context: ADK ToolContext (optional)
        
    Returns:
        Result (possibly updated with artifact info)
    """
    try:
        return _artifact_generator.ensure_artifact_generated(
            tool_name, result, tool_context
        )
    except Exception as e:
        logger.error(f"[ARTIFACT GEN] Critical failure in ensure_artifact_for_tool: {e}")
        # Return original result unchanged
        return result


def get_artifact_stats() -> Dict[str, int]:
    """Get global artifact generation statistics."""
    return _artifact_generator.get_stats()


# Wrapper decorator for easy integration
def with_artifact_generation(func):
    """
    Decorator to ensure artifact generation for a tool function.
    
    Usage:
        @with_artifact_generation
        def my_tool(param1, param2, tool_context=None):
            return {"status": "success", "data": "..."}
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Execute original function
        result = func(*args, **kwargs)
        
        # Extract tool_context if present
        tool_context = kwargs.get('tool_context')
        if not tool_context and args:
            # Check if any arg has 'state' attribute (likely ToolContext)
            for arg in args:
                if hasattr(arg, 'state') and hasattr(arg, 'save_artifact'):
                    tool_context = arg
                    break
        
        # Ensure artifact generation
        result = ensure_artifact_for_tool(func.__name__, result, tool_context)
        
        return result
    
    return wrapper

