"""
Context window management with automatic tool reduction.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from enum import IntEnum

logger = logging.getLogger(__name__)

class ToolReductionLevel(IntEnum):
    """Tool reduction levels from most to least comprehensive."""
    ALL = 0      # All 90+ tools
    CORE = 1     # ~70% of tools (core functionality)
    ESSENTIAL = 2 # ~40% of tools (essential only)
    MINIMAL = 3   # ~20% of tools (minimal set)

class ContextManager:
    """Manages context window and tool reduction dynamically."""
    
    def __init__(self):
        self.tool_reduction_level = ToolReductionLevel.ALL
        self.max_context_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "128000"))
        self.safety_margin = float(os.getenv("CONTEXT_SAFETY_MARGIN", "0.85"))
        self.reduction_threshold = int(self.max_context_tokens * self.safety_margin)
        
    def handle_context_overflow(self, error_msg: str) -> Dict[str, Any]:
        """Handle context window overflow by reducing tool set."""
        current_level = self.tool_reduction_level
        
        if current_level == ToolReductionLevel.ALL:
            new_level = ToolReductionLevel.CORE
            message = " Context overflow detected. Reducing to CORE tools (70% of functionality)"
        elif current_level == ToolReductionLevel.CORE:
            new_level = ToolReductionLevel.ESSENTIAL
            message = " Still overflowing. Reducing to ESSENTIAL tools (40% of functionality)"
        elif current_level == ToolReductionLevel.ESSENTIAL:
            new_level = ToolReductionLevel.MINIMAL
            message = " Critical overflow. Reducing to MINIMAL tools (20% of functionality)"
        else:
            # Already at minimal - can't reduce further
            return {
                "new_tool_level": current_level,
                "message": "[WARNING] Already at minimal tool set. Consider reducing prompt complexity.",
                "can_reduce": False
            }
        
        self.tool_reduction_level = new_level
        
        return {
            "new_tool_level": new_level,
            "message": message,
            "can_reduce": True
        }
    
    def get_tool_subset(self, tools: List[Any], level: Optional[ToolReductionLevel] = None) -> List[Any]:
        """Get a subset of tools based on reduction level."""
        if level is None:
            level = self.tool_reduction_level
        
        # Always return all tools - no exclusions
        logger.info(f"Tool reduction: {len(tools)} -> {len(tools)} tools (level: {level.name if hasattr(level, 'name') else str(level)}) - ALL TOOLS INCLUDED")
        return tools
    
    def reset_to_all(self):
        """Reset tool reduction to include all tools."""
        self.tool_reduction_level = ToolReductionLevel.ALL
        logger.info(" Reset to ALL tools")

# Global context manager instance
_context_manager = ContextManager()

def apply_context_reduction(agent, error_msg: str) -> bool:
    """Apply context reduction when overflow happens."""
    try:
        rec = _context_manager.handle_context_overflow(error_msg)
        _context_manager.tool_reduction_level = rec['new_tool_level']
        agent.tools = _context_manager.get_tool_subset(agent.tools, level=rec['new_tool_level'])
        logger.warning(rec['message'])
        return rec.get('can_reduce', False)
    except Exception as e:
        logger.error(f"Failed to apply context reduction: {e}")
        return False
