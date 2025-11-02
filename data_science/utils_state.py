"""
State management helpers with ADK-recommended prefixes.
"""
from typing import Any, Optional, Dict


def get_user(tool_context, key: str, default=None) -> Any:
    """Get user-scoped state value."""
    if not tool_context:
        return default
    return tool_context.state.get(f"user:{key}", default)


def set_user(tool_context, key: str, value: Any) -> None:
    """Set user-scoped state value."""
    if tool_context:
        tool_context.state[f"user:{key}"] = value


def get_app(tool_context, key: str, default=None) -> Any:
    """Get app-scoped state value."""
    if not tool_context:
        return default
    return tool_context.state.get(f"app:{key}", default)


def set_app(tool_context, key: str, value: Any) -> None:
    """Set app-scoped state value."""
    if tool_context:
        tool_context.state[f"app:{key}"] = value


def get_temp(tool_context, key: str, default=None) -> Any:
    """Get temporary state value."""
    if not tool_context:
        return default
    return tool_context.state.get(f"temp:{key}", default)


def set_temp(tool_context, key: str, value: Any) -> None:
    """Set temporary state value."""
    if tool_context:
        tool_context.state[f"temp:{key}"] = value


def clear_temp(tool_context, key: str = None) -> None:
    """Clear temporary state (all or specific key)."""
    if not tool_context:
        return
    if key:
        temp_key = f"temp:{key}"
        if temp_key in tool_context.state:
            del tool_context.state[temp_key]
    else:
        # Clear all temp keys
        # ADK State object may not support .keys(), try dict-like access
        try:
            if hasattr(tool_context.state, 'keys'):
                keys_to_remove = [k for k in tool_context.state.keys() if k.startswith("temp:")]
            else:
                # If State doesn't support keys(), we can't iterate - log and skip
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("State object doesn't support .keys(), cannot bulk-clear temp: keys")
                keys_to_remove = []
            for k in keys_to_remove:
                del tool_context.state[k]
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not clear temp state keys: {e}")


def get_context_info(tool_context) -> Dict[str, str]:
    """Get context information for logging/telemetry."""
    if not tool_context:
        return {"agent": "unknown", "invocation": "unknown", "function": "n/a"}
    
    return {
        "agent": getattr(tool_context, "agent_name", "unknown-agent"),
        "invocation": getattr(tool_context, "invocation_id", "unknown-invocation"),
        "function": getattr(tool_context, "function_call_id", "n/a")
    }
