"""
LLM-exposed routers that dispatch to the internal registries.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from .internal_registry import TOOL_REGISTRY, list_available_actions

def route_user_intent_tool(action: str, params: str = "{}"):
    """Generic router: dispatch to any internal tool by action name.
    params must be a JSON string (ADK-compatible).
    """
    try:
        # Hard-route plot aliases to the plot tool
        PLOT_ALIASES = {"plot", "plots", "visualize", "visualisation", "visualization", "chart", "charts", "eda_plots"}
        action_lc = (action or "").strip().lower()
        if action_lc in PLOT_ALIASES:
            # hard-route to the tool; do not let LLM free-form respond
            from .plot_tool_guard import plot_tool_guard  # use guard to guarantee artifacts
            from google.adk.tools import ToolContext
            return plot_tool_guard(tool_context=ToolContext.current())
        
        # Auto-trigger head and describe after data analysis
        ANALYSIS_ACTIONS = {"analyze", "analysis", "data_analysis", "eda", "exploratory"}
        if action_lc in ANALYSIS_ACTIONS:
            from .auto_analysis_guard import auto_analysis_guard
            from google.adk.tools import ToolContext
            return auto_analysis_guard(tool_context=ToolContext.current())
        
        # Handle unstructured data actions
        UNSTRUCTURED_ACTIONS = {"unstructured", "process_unstructured", "list_unstructured", "analyze_unstructured"}
        if action_lc in UNSTRUCTURED_ACTIONS:
            from .unstructured_tools import process_unstructured_tool, list_unstructured_tool, analyze_unstructured_tool
            from google.adk.tools import ToolContext
            tool_context = ToolContext.current()
            
            if action_lc == "list_unstructured":
                return list_unstructured_tool(tool_context=tool_context)
            elif action_lc == "analyze_unstructured":
                payload = json.loads(params or "{}")
                return analyze_unstructured_tool(tool_context=tool_context, **payload)
            else:
                payload = json.loads(params or "{}")
                return process_unstructured_tool(tool_context=tool_context, **payload)
        
        fn = TOOL_REGISTRY.get(action)
        if not fn:
            return {
                "error": f"Unknown action '{action}'",
                "available": list_available_actions(),
            }
        payload = json.loads(params or "{}")
        # Call tool (wrappers are JSON-friendly and may be sync)
        return fn(**payload)
    except Exception as e:
        return {"error": str(e), "status": "failed", "action": action}
