"""
Observability & metrics plugin for global monitoring.
Tracks counts, timings, and token usage across all operations.
"""
import time
import logging

# Fallback base plugin if ADK plugins not available
try:
    from google.adk.plugins.base_plugin import BasePlugin
except ImportError:
    class BasePlugin:
        def __init__(self, name="fallback"):
            self.name = name
        async def before_agent_callback(self, **kwargs): return None
        async def after_agent_callback(self, **kwargs): return None
        async def before_model_callback(self, **kwargs): return None
        async def after_model_callback(self, **kwargs): return None
        async def before_tool_callback(self, **kwargs): return None
        async def after_tool_callback(self, **kwargs): return None
        async def on_tool_error_callback(self, **kwargs): return None

logger = logging.getLogger(__name__)

class ObservabilityPlugin(BasePlugin):
    """Plugin for observability, metrics, and performance tracking."""
    
    def __init__(self):
        super().__init__(name="observability")
        self._timers = {}
        self._metrics = {
            "agent_calls": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "total_tokens": 0,
            "errors": 0
        }
    
    async def before_agent_callback(self, *, agent, callback_context, **kwargs):
        """Track agent execution start."""
        self._timers["agent"] = time.time()
        self._metrics["agent_calls"] += 1
        logger.debug(f"[obs] Starting agent: {getattr(agent, 'name', 'unknown')}")
    
    async def after_agent_callback(self, *, agent, callback_context, result, **kwargs):
        """Track agent execution completion."""
        duration = time.time() - self._timers.pop("agent", time.time())
        logger.info(f"[obs] agent={getattr(agent, 'name', 'unknown')} {duration:.2f}s")
        
        # Store metrics in context for downstream use
        if hasattr(callback_context, 'state'):
            callback_context.state["metrics:agent_duration"] = duration
            callback_context.state["metrics:agent_calls"] = self._metrics["agent_calls"]
    
    async def before_model_callback(self, *, callback_context, llm_request, **kwargs):
        """Track model call start."""
        self._timers["model"] = time.time()
        self._metrics["model_calls"] += 1
        model_name = getattr(llm_request, 'model', 'unknown')
        logger.debug(f"[obs] Starting model call: {model_name}")
    
    async def after_model_callback(self, *, callback_context, llm_request, llm_response, **kwargs):
        """Track model call completion and token usage."""
        duration = time.time() - self._timers.pop("model", time.time())
        
        # Extract token usage if available
        usage = getattr(llm_response, "usage", None)
        token_count = 0
        if usage:
            if hasattr(usage, "total_tokens"):
                token_count = usage.total_tokens
            elif hasattr(usage, "prompt_tokens") and hasattr(usage, "completion_tokens"):
                token_count = usage.prompt_tokens + usage.completion_tokens
        
        self._metrics["total_tokens"] += token_count
        
        logger.info(f"[obs] model {duration:.2f}s usage={usage} tokens={token_count}")
        
        # Store metrics in context
        if hasattr(callback_context, 'state'):
            callback_context.state["metrics:model_duration"] = duration
            callback_context.state["metrics:model_tokens"] = token_count
            callback_context.state["metrics:total_tokens"] = self._metrics["total_tokens"]
    
    async def before_tool_callback(self, *, tool, tool_args, tool_context, **kwargs):
        """Track tool execution start."""
        timer_key = f"tool:{getattr(tool, 'name', 'unknown')}"
        self._timers[timer_key] = time.time()
        self._metrics["tool_calls"] += 1
        logger.debug(f"[obs] Starting tool: {getattr(tool, 'name', 'unknown')}")
    
    async def after_tool_callback(self, *, tool, tool_args, tool_context, result, **kwargs):
        """Track tool execution completion."""
        timer_key = f"tool:{getattr(tool, 'name', 'unknown')}"
        duration = time.time() - self._timers.pop(timer_key, time.time())
        status = result.get("status", "ok") if isinstance(result, dict) else "ok"
        
        logger.info(f"[obs] tool={getattr(tool, 'name', 'unknown')} {duration:.2f}s status={status}")
        
        # Store metrics in context
        if hasattr(tool_context, 'state'):
            tool_context.state["metrics:last_tool_duration"] = duration
            tool_context.state["metrics:last_tool_status"] = status
            tool_context.state["metrics:tool_calls"] = self._metrics["tool_calls"]
    
    async def on_tool_error_callback(self, *, tool, tool_args, tool_context, error, **kwargs):
        """Track tool errors."""
        self._metrics["errors"] += 1
        logger.error(f"[obs] tool={getattr(tool, 'name', 'unknown')} error: {str(error)}")
        
        # Store error metrics
        if hasattr(tool_context, 'state'):
            tool_context.state["metrics:errors"] = self._metrics["errors"]
            tool_context.state["metrics:last_error"] = str(error)
    
    def get_metrics(self) -> dict:
        """Get current metrics summary."""
        return {
            **self._metrics,
            "active_timers": len(self._timers)
        }
