"""
Safe ToolContext shim to avoid builtins mutation.
"""
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

# Safe import without mutating builtins
try:
    from google.adk.tools import ToolContext as _ToolContext  # type: ignore
    _TOOLCONTEXT_AVAILABLE = True
except ImportError:
    _TOOLCONTEXT_AVAILABLE = False
    logger.warning("ToolContext not available - using fallback")

# Safe ToolContext shim
if _TOOLCONTEXT_AVAILABLE:
    ToolContext = _ToolContext
else:
    class ToolContext:
        """Fallback ToolContext when ADK is not available."""
        
        def __init__(self, *args, **kwargs):
            self.state: Dict[str, Any] = {}
            self.artifacts: list = []
            
        def save_artifact(self, filename: str, artifact: Any) -> None:
            """Fallback artifact saving."""
            logger.warning(f"Fallback artifact save: {filename}")
            
        async def save_artifact(self, filename: str, artifact: Any) -> None:
            """Async fallback artifact saving."""
            logger.warning(f"Async fallback artifact save: {filename}")

def get_safe_toolcontext() -> type:
    """
    Get the safe ToolContext class.
    
    Returns:
        ToolContext class (real or fallback)
    """
    return ToolContext

def is_toolcontext_available() -> bool:
    """
    Check if real ToolContext is available.
    
    Returns:
        True if real ToolContext available, False if using fallback
    """
    return _TOOLCONTEXT_AVAILABLE
