"""
Result Validation System

Validates that tool results contain actual data/results and logs warnings when they don't.
This ensures all tools produce meaningful outputs that can be tracked.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Tools logger for result validation
try:
    from .logging_config import get_tools_logger
    tools_logger = get_tools_logger()
except ImportError:
    tools_logger = logger


def validate_tool_result(tool_name: str, result: Any, throw_exception: bool = False) -> tuple[bool, Optional[str]]:
    """
    Validate that a tool result contains actual data/results.
    
    Checks for:
    - Display fields (__display__, message, ui_text, content, text)
    - Data fields (data, result, metrics, overview, summary, insights)
    - Status indicating success
    - Non-empty content
    
    Args:
        tool_name: Name of the tool
        result: Tool result (dict, list, str, etc.)
        throw_exception: If True, raises exception on validation failure (but continues execution)
        
    Returns:
        (has_results: bool, warning_message: Optional[str])
        
    Side Effects:
        Logs warning/error to tools.log if no results found
    """
    if result is None:
        warning_msg = f"Tool '{tool_name}' returned None - no results generated"
        tools_logger.error(f"[RESULT VALIDATION] ✗ {warning_msg}")
        if throw_exception:
            logger.error(f"[RESULT VALIDATION] {warning_msg}")
        return False, warning_msg
    
    # Check if result is a dict
    if isinstance(result, dict):
        # Check for explicit error/failure status
        if result.get("status") == "error" or result.get("status") == "failed":
            # This is an error, not missing results - skip validation
            return True, None
        
        # Check for display fields with content
        display_fields = ["__display__", "message", "ui_text", "content", "text", "display", "_formatted_output"]
        has_display = False
        display_content = None
        
        for field in display_fields:
            value = result.get(field)
            if value and isinstance(value, str) and len(value.strip()) > 0:
                has_display = True
                display_content = value
                break
        
        # Check for data fields
        data_fields = ["data", "result", "metrics", "overview", "summary", "insights", "shape", "columns"]
        has_data = False
        data_content = None
        
        for field in data_fields:
            value = result.get(field)
            if value is not None:
                # Check if it's meaningful (not empty dict/list)
                if isinstance(value, dict) and len(value) > 0:
                    has_data = True
                    data_content = field
                    break
                elif isinstance(value, list) and len(value) > 0:
                    has_data = True
                    data_content = field
                    break
                elif isinstance(value, (str, int, float, bool)):
                    has_data = True
                    data_content = field
                    break
        
        # Check for nested result dict
        if "result" in result and isinstance(result["result"], dict):
            nested_has_data, _ = validate_tool_result(f"{tool_name}.nested", result["result"], throw_exception=False)
            if nested_has_data:
                has_data = True
                data_content = "result.nested"
        
        # Validation: Must have either display content OR data content
        if not has_display and not has_data:
            warning_msg = (
                f"Tool '{tool_name}' returned result with NO visible data:\n"
                f"  - No display fields found with content (checked: {', '.join(display_fields)})\n"
                f"  - No data fields found with content (checked: {', '.join(data_fields)})\n"
                f"  - Result keys: {list(result.keys())}\n"
                f"  - Status: {result.get('status', 'unknown')}"
            )
            tools_logger.error(f"[RESULT VALIDATION] ✗ {warning_msg}")
            logger.error(f"[RESULT VALIDATION] Tool '{tool_name}' has no results: {list(result.keys())}")
            if throw_exception:
                # Raise exception but don't stop execution (this will be caught)
                raise ValueError(f"Tool '{tool_name}' result validation failed: No results found")
            return False, warning_msg
        else:
            # Success - log what was found
            result_type = "display" if has_display else "data"
            result_field = display_content if has_display else data_content
            tools_logger.info(
                f"[RESULT VALIDATION] ✅ Tool '{tool_name}' has results "
                f"({result_type}: {result_field if isinstance(result_field, str) else 'found'})"
            )
            return True, None
    
    elif isinstance(result, str):
        # String result
        if len(result.strip()) > 0:
            tools_logger.info(f"[RESULT VALIDATION] ✅ Tool '{tool_name}' has string result ({len(result)} chars)")
            return True, None
        else:
            warning_msg = f"Tool '{tool_name}' returned empty string - no results"
            tools_logger.error(f"[RESULT VALIDATION] ✗ {warning_msg}")
            if throw_exception:
                raise ValueError(f"Tool '{tool_name}' result validation failed: Empty string")
            return False, warning_msg
    
    elif isinstance(result, (list, tuple)):
        # List/tuple result
        if len(result) > 0:
            tools_logger.info(f"[RESULT VALIDATION] ✅ Tool '{tool_name}' has list result ({len(result)} items)")
            return True, None
        else:
            warning_msg = f"Tool '{tool_name}' returned empty list - no results"
            tools_logger.error(f"[RESULT VALIDATION] ✗ {warning_msg}")
            if throw_exception:
                raise ValueError(f"Tool '{tool_name}' result validation failed: Empty list")
            return False, warning_msg
    
    else:
        # Other types (int, float, bool) - always valid
        tools_logger.info(f"[RESULT VALIDATION] ✅ Tool '{tool_name}' has result (type: {type(result).__name__})")
        return True, None


def ensure_result_tracking(tool_name: str, result: Any) -> Dict[str, Any]:
    """
    Ensure tool result is tracked and validated.
    
    This function:
    1. Validates result has data
    2. Adds tracking metadata
    3. Logs to tools.log
    4. Returns enhanced result with tracking info
    
    Args:
        tool_name: Name of the tool
        result: Tool result
        
    Returns:
        Enhanced result with tracking metadata (if dict) or original result
    """
    # Validate result has data (but don't throw - just log)
    has_results, warning_msg = validate_tool_result(tool_name, result, throw_exception=False)
    
    # Add tracking metadata if result is a dict
    if isinstance(result, dict):
        result["_result_validated"] = has_results
        result["_result_tracking"] = {
            "tool_name": tool_name,
            "has_results": has_results,
            "validation_warning": warning_msg,
            "tracked_at": __import__("datetime").datetime.now().isoformat()
        }
        
        if not has_results:
            # Add warning to result itself
            result.setdefault("warnings", []).append("Result validation: No visible data found in result")
            result.setdefault("_validation_failed", True)
    
    return result
