"""
Runner setup with plugins for the Data Science Agent.
Creates a runner with all plugins configured.
"""
import os
import logging
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from .plugins.observability_plugin import ObservabilityPlugin
from .plugins.policy_plugin import PolicyPlugin
from .plugins.cache_plugin import CachePlugin
from .plugins.prompt_plugin import PromptPlugin
from .agent import root_agent
from .context_manager import _context_manager

logger = logging.getLogger(__name__)

def create_runner_with_plugins():
    """Create a runner with all plugins configured."""
    
    # Configure plugin parameters from environment
    cache_ttl = int(os.getenv("CACHE_TTL_SECONDS", "900"))  # 15 minutes default
    system_hint = os.getenv("SYSTEM_HINT", "Follow staged DS workflow; keep outputs concise.")
    
    # Create plugins
    plugins = [
        ObservabilityPlugin(),
        PolicyPlugin(),
        CachePlugin(ttl_s=cache_ttl),
        PromptPlugin(system_hint=system_hint)
    ]
    
    logger.info(f"Created runner with {len(plugins)} plugins")
    
    # Create runner with plugins
    runner = InMemoryRunner(
        agent=root_agent,
        app_name='data_science_with_plugins',
        plugins=plugins,
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )
    
    return runner

def handle_context_overflow(runner, session_state):
    """Handle context overflow by reducing tools."""
    if session_state.get("ctx:overflow") == "true":
        logger.warning("Context overflow detected, reducing tools")
        
        # Reduce tool level
        current_level = _context_manager.tool_reduction_level
        if current_level < 3:  # Not already at minimal
            _context_manager.tool_reduction_level = current_level + 1
            root_agent.tools = _context_manager.get_tool_subset(
                root_agent.tools, 
                level=_context_manager.tool_reduction_level
            )
            logger.info(f"Reduced tools to level {_context_manager.tool_reduction_level.name}")
        
        # Clear overflow flag
        session_state["ctx:overflow"] = "false"
        session_state["ctx:overflow_resolved"] = "true"
        
        return True
    
    return False

# Global runner instance
_runner = None

def get_runner():
    """Get or create the global runner instance."""
    global _runner
    if _runner is None:
        _runner = create_runner_with_plugins()
    return _runner
