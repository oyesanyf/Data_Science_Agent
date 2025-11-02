"""
Auto-analysis guard that runs head and describe after data analysis.
"""
from typing import Any, Dict
from .head_describe_guard import head_tool_guard, describe_tool_guard

def auto_analysis_guard(tool_context=None, **kwargs) -> Dict[str, Any]:
    """
    Automatically runs head and describe after data analysis to show:
    - Data preview (head)
    - Data summary (describe)
    - Both outputs in chat and artifacts
    """
    results = []
    
    # Run head tool first
    try:
        head_result = head_tool_guard(tool_context=tool_context, **kwargs)
        results.append(" Data preview generated")
        if isinstance(head_result, dict) and head_result.get("message"):
            results.append(head_result["message"])
    except Exception as e:
        results.append(f"[WARNING] Head tool failed: {str(e)}")
    
    # Run describe tool
    try:
        describe_result = describe_tool_guard(tool_context=tool_context, **kwargs)
        results.append(" Data summary generated")
        if isinstance(describe_result, dict) and describe_result.get("message"):
            results.append(describe_result["message"])
    except Exception as e:
        results.append(f"[WARNING] Describe tool failed: {str(e)}")
    
    # Combine results
    combined_message = "\n".join(results)
    
    return {
        "status": "success",
        "message": combined_message,
        "ui_text": combined_message,
        "analysis_complete": True,
        "head_run": True,
        "describe_run": True
    }
