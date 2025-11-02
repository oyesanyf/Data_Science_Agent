"""
Optional helper for structured output support with SequentialAgent fallback.

This provides a before_model_callback that can conditionally enable
structured output schema when needed, while keeping tools available.

Also supports SequentialAgent as fallback when:
- output_schema + tools fails
- Explicit structured output is requested
- Tool execution needs formatting recovery
"""

import json
import logging
from typing import Optional, Dict, Any
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest

logger = logging.getLogger(__name__)

# Global flag to track if we should use SequentialAgent fallback
_use_sequential_fallback = False


def set_use_sequential_fallback(enabled: bool = True):
    """Enable/disable SequentialAgent fallback mode."""
    global _use_sequential_fallback
    _use_sequential_fallback = enabled
    logger.info(f"[STRUCTURED OUTPUT] SequentialAgent fallback: {'enabled' if enabled else 'disabled'}")


def should_use_sequential_fallback(user_message: str = "") -> bool:
    """
    Determine if SequentialAgent fallback should be used.
    
    Args:
        user_message: Current user message (checked for structured output keywords)
    
    Returns:
        True if should use SequentialAgent fallback
    """
    global _use_sequential_fallback
    
    # Check global flag first
    if _use_sequential_fallback:
        return True
    
    # Check for explicit structured output requests
    structured_keywords = [
        "structured output",
        "json schema",
        "pydantic schema",
        "schema format",
        "structured response",
        "json format",
        "use sequential",
        "format agent",
    ]
    
    user_lower = user_message.lower() if user_message else ""
    if any(keyword in user_lower for keyword in structured_keywords):
        logger.info("[STRUCTURED OUTPUT] Detected structured output request, will use SequentialAgent fallback")
        return True
    
    return False


def set_structured_output_conditional(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
    output_schema: Optional[dict] = None,
    schema_detection: bool = False,
    check_sequential_fallback: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Conditionally set structured output schema with SequentialAgent fallback support.
    
    Can detect schema from prompt or use provided schema.
    If schema is detected/set, tries native ADK support first.
    Falls back to SequentialAgent if needed.
    
    Args:
        callback_context: ADK callback context
        llm_request: LLM request being prepared
        output_schema: Optional pre-defined schema dict
        schema_detection: If True, scan prompt for ```jsonSchema blocks
        check_sequential_fallback: If True, check if SequentialAgent fallback is needed
    
    Returns:
        Dict with fallback info if SequentialAgent should be used, None otherwise
    """
    if not llm_request.contents or not llm_request.contents[-1].parts:
        return None
    
    # Extract user message to check for structured output requests
    user_message = ""
    try:
        if llm_request.contents and llm_request.contents[-1].parts:
            for part in llm_request.contents[-1].parts:
                if hasattr(part, 'text') and part.text:
                    user_message += part.text
    except Exception:
        pass
    
    # Check if SequentialAgent fallback is needed
    if check_sequential_fallback and should_use_sequential_fallback(user_message):
        logger.info("[STRUCTURED OUTPUT] SequentialAgent fallback requested")
        return {
            "use_sequential_fallback": True,
            "reason": "User requested structured output or fallback enabled",
            "user_message": user_message[:200]  # Truncate for logging
        }
    
    # Try native ADK support first (v1.11.0+)
    schema_dict = None
    
    # If schema provided directly, use it
    if output_schema:
        if isinstance(output_schema, dict):
            schema_dict = output_schema
        else:
            # Assume Pydantic model - convert to dict
            try:
                schema_dict = output_schema.model_json_schema() if hasattr(output_schema, 'model_json_schema') else None
            except Exception:
                logger.warning("[STRUCTURED OUTPUT] Could not convert schema to dict")
    
    # Detect from prompt if enabled
    if not schema_dict and schema_detection:
        SCHEMA_START = '```jsonSchema\n'
        SCHEMA_END = '\n```'
        
        last_parts = llm_request.contents[-1].parts
        
        for i in range(len(last_parts) - 1, -1, -1):
            part = last_parts[i]
            if (
                part.text
                and part.text.startswith(SCHEMA_START)
                and part.text.endswith(SCHEMA_END)
            ):
                try:
                    schema_text = part.text.removeprefix(SCHEMA_START).removesuffix(SCHEMA_END)
                    schema_dict = json.loads(schema_text)
                    
                    # Remove schema block from prompt (already in config)
                    del last_parts[i]
                    break
                except Exception as e:
                    logger.warning(f"[STRUCTURED OUTPUT] Failed to parse schema: {e}")
                    continue
    
    # Set structured output if schema found
    if schema_dict:
        try:
            llm_request.config.response_json_schema = schema_dict
            llm_request.config.response_mime_type = 'application/json'
            
            # ADK v1.11.0+ supports tools + output_schema
            # If this fails, we'll fall back to SequentialAgent
            logger.info("[STRUCTURED OUTPUT] Enabled structured output with tools (native ADK)")
            return None
        except Exception as e:
            # Native support failed - signal SequentialAgent fallback
            logger.warning(f"[STRUCTURED OUTPUT] Native schema support failed: {e}, will use SequentialAgent fallback")
            if check_sequential_fallback:
                return {
                    "use_sequential_fallback": True,
                    "reason": f"Native schema support failed: {e}",
                    "schema": schema_dict
                }
    
    return None

