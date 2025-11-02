"""
LLM Post-Processor: Automatically inject tool outputs when LLM fails to show them.

This middleware ensures users ALWAYS see tool results, regardless of LLM behavior.
"""
import logging
import re

logger = logging.getLogger(__name__)

def inject_tool_outputs(llm_response: str, tool_calls_history: list) -> str:
    """
    Inject tool outputs if LLM didn't show them.
    
    This is a SAFETY NET for when the LLM ignores tool outputs despite explicit instructions.
    
    Args:
        llm_response: The LLM's generated response text
        tool_calls_history: List of (tool_name, tool_result) tuples from this turn
    
    Returns:
        Enhanced response with tool outputs if LLM failed to show them
    """
    if not tool_calls_history:
        # No tools were called - nothing to inject
        return llm_response
    
    # Step 1: Check if LLM actually showed meaningful data
    data_indicators = [
        'rows', 'columns', 'mean:', 'std:', 'min:', 'max:', 
        'dataset has', 'shape:', 'total:', 'count:', 'type:',
        'rows ×', 'rows x', 'dtype', 'null', 'missing',
        'feature', 'correlation', 'distribution'
    ]
    
    has_data = any(indicator in llm_response.lower() for indicator in data_indicators)
    
    # Check if LLM said generic "no data" phrases
    no_data_phrases = [
        'no visible', 'no data', 'no results', 'no specific',
        'did not return', 'didn\'t return', 'no outputs',
        'not provided', 'no information', 'empty result'
    ]
    
    says_no_data = any(phrase in llm_response.lower() for phrase in no_data_phrases)
    
    if has_data and not says_no_data:
        logger.info("[POST-PROCESSOR] LLM showed data correctly - no injection needed")
        return llm_response
    
    # Step 2: LLM failed - extract and inject tool outputs
    logger.warning("[POST-PROCESSOR] LLM did NOT show data - injecting tool outputs automatically")
    
    injected_outputs = []
    for tool_name, tool_result in tool_calls_history:
        if not isinstance(tool_result, dict):
            continue
        
        # Skip if tool returned an error
        if tool_result.get("status") == "error":
            continue
        
        # Extract display field (priority order)
        display = (tool_result.get("__display__") or
                  tool_result.get("message") or
                  tool_result.get("text") or
                  tool_result.get("ui_text") or
                  tool_result.get("content") or
                  tool_result.get("display") or
                  tool_result.get("_formatted_output") or "")
        
        if display and len(display) > 10:  # Meaningful content only
            # Clean tool name for display
            clean_name = tool_name.replace("_tool", "").replace("_", " ").title()
            injected_outputs.append(f"\n📊 **{clean_name} Results:**\n\n{display}\n")
            logger.info(f"[POST-PROCESSOR] Injecting output from {tool_name} ({len(display)} chars)")
    
    if not injected_outputs:
        logger.warning("[POST-PROCESSOR] No displayable tool outputs found")
        return llm_response
    
    # Step 3: Build enhanced response
    # Remove the LLM's "no data" statement if present
    if says_no_data:
        # Replace generic "no data" statements
        for phrase in no_data_phrases:
            llm_response = re.sub(
                rf'.*{re.escape(phrase)}.*\n?', 
                '', 
                llm_response, 
                flags=re.IGNORECASE
            )
    
    # Prepend tool outputs to LLM response
    enhanced = (
        f"{''.join(injected_outputs)}\n"
        f"{'─' * 80}\n\n"
        f"{llm_response.strip()}"
    )
    
    logger.info(f"[POST-PROCESSOR] ✅ Injected {len(injected_outputs)} tool outputs")
    return enhanced


def track_tool_call(tool_name: str, tool_result: dict, session_state: dict) -> None:
    """
    Track tool calls in session state for later injection.
    
    Args:
        tool_name: Name of the tool that was called
        tool_result: Result dictionary from the tool
        session_state: Session state dict to store history
    """
    if "tool_calls_history" not in session_state:
        session_state["tool_calls_history"] = []
    
    session_state["tool_calls_history"].append((tool_name, tool_result))
    logger.debug(f"[TOOL-TRACKER] Tracked {tool_name}, history size: {len(session_state['tool_calls_history'])}")


def reset_tool_history(session_state: dict) -> None:
    """
    Reset tool call history at the start of a new user turn.
    
    Args:
        session_state: Session state dict
    """
    session_state["tool_calls_history"] = []
    logger.debug("[TOOL-TRACKER] Reset tool history for new turn")


def get_tool_history(session_state: dict) -> list:
    """
    Get tool call history for current turn.
    
    Args:
        session_state: Session state dict
    
    Returns:
        List of (tool_name, tool_result) tuples
    """
    return session_state.get("tool_calls_history", [])

