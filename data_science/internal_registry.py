"""
Internal tool registry (NOT exposed to LLM).

Maps action names to callables. We auto-populate from adk_safe_wrappers by
collecting all functions ending with `_tool` and exposing them by their base
name (without the suffix). This keeps 150+ functions available without
registering them with the LLM.
"""
from typing import Dict, Callable, Any

TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {}

def _build_registry() -> Dict[str, Callable[..., Any]]:
    try:
        # Import ADK-safe wrappers (JSON-friendly signatures)
        from . import adk_safe_wrappers as wrappers  # type: ignore
    except Exception:
        return {}

    registry: Dict[str, Callable[..., Any]] = {}
    for name, fn in wrappers.__dict__.items():
        if callable(fn) and name.endswith('_tool'):
            base = name[:-5]  # strip `_tool`
            # Avoid collisions; last one wins if duplicates
            registry[base] = fn
    return registry

# Initialize once at import
TOOL_REGISTRY = _build_registry()

def list_available_actions(max_items: int = 200) -> list:
    return sorted(list(TOOL_REGISTRY.keys()))[:max_items]


