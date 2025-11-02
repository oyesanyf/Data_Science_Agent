"""
Tool safety utilities to prevent ADK context exposure in schemas.
"""
import inspect
from typing import get_type_hints, Any, Callable
from .ds_tools import ensure_display_fields


# ADK context types that should never appear in tool signatures
_FORBIDDEN_TYPES = {
    "CallbackContext", 
    "InvocationContext", 
    "ReadonlyContext", 
    "ToolContext",
    "google.adk.agents.callback_context.CallbackContext",
    "google.adk.tools.tool_context.ToolContext"
}


@ensure_display_fields
def assert_json_signature(fn: Callable) -> Callable:
    """
    Validate that a function only uses JSON-serializable parameters.
    Raises TypeError if ADK context types are found in the signature.
    """
    try:
        hints = get_type_hints(fn, include_extras=True)
        sig = inspect.signature(fn)
        
        # Check parameter annotations
        for param_name, param in sig.parameters.items():
            if param.annotation:
                type_str = str(param.annotation)
                for forbidden in _FORBIDDEN_TYPES:
                    if forbidden in type_str:
                        raise TypeError(
                            f"{fn.__name__} exposes ADK context type '{forbidden}' in parameter '{param_name}'. "
                            f"Use a wrapper with **kwargs to capture tool_context."
                        )
        
        # Check return type annotations
        if 'return' in hints:
            return_type_str = str(hints['return'])
            for forbidden in _FORBIDDEN_TYPES:
                if forbidden in return_type_str:
                    raise TypeError(
                        f"{fn.__name__} has ADK context type '{forbidden}' in return annotation. "
                        f"Return only JSON-serializable types."
                    )
        
        return fn
        
    except Exception as e:
        if "ADK context" in str(e):
            raise
        # If type hint inspection fails, that's okay - we'll catch it at runtime
        return fn


@ensure_display_fields
def create_adk_safe_wrapper(original_func: Callable, wrapper_name: str = None) -> Callable:
    """
    Create an ADK-safe wrapper for a function that uses ToolContext.
    
    Args:
        original_func: The original function that takes tool_context parameter
        wrapper_name: Optional name for the wrapper function
        
    Returns:
        ADK-safe wrapper function that captures tool_context via **kwargs
    """
    if wrapper_name is None:
        wrapper_name = f"{original_func.__name__}_tool"
    
    def wrapper(*args, **kwargs):
        # Extract tool_context from kwargs (ADK injects this)
        tool_context = kwargs.pop("tool_context", None)
        
        # Call original function with tool_context
        return original_func(*args, tool_context=tool_context, **kwargs)
    
    # Copy metadata
    wrapper.__name__ = wrapper_name
    wrapper.__doc__ = original_func.__doc__
    wrapper.__module__ = original_func.__module__
    
    # Validate the wrapper signature
    assert_json_signature(wrapper)
    
    return wrapper


@ensure_display_fields
def validate_tool_registration(tool_func: Callable) -> None:
    """
    Validate that a tool function is safe for ADK registration.
    Should be called before registering any tool.
    """
    try:
        assert_json_signature(tool_func)
    except TypeError as e:
        raise ValueError(f"Cannot register {tool_func.__name__}: {e}")


# Example usage patterns for common tool patterns
@ensure_display_fields
def create_simple_tool_wrapper(original_func: Callable) -> Callable:
    """Create a simple wrapper for functions that only need tool_context."""
    def wrapper(**kwargs):
        tool_context = kwargs.get("tool_context")
        return original_func(tool_context=tool_context)
    
    wrapper.__name__ = f"{original_func.__name__}_tool"
    wrapper.__doc__ = original_func.__doc__
    assert_json_signature(wrapper)
    return wrapper


@ensure_display_fields
def create_csv_tool_wrapper(original_func: Callable) -> Callable:
    """Create a wrapper for CSV-based tools that take csv_path and tool_context."""
    def wrapper(csv_path: str = "", **kwargs):
        tool_context = kwargs.get("tool_context")
        return original_func(csv_path=csv_path, tool_context=tool_context)
    
    wrapper.__name__ = f"{original_func.__name__}_tool"
    wrapper.__doc__ = original_func.__doc__
    assert_json_signature(wrapper)
    return wrapper
