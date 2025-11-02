"""
Response cache plugin for LLM and Tool calls.
Complements backoff & circuit breaker by avoiding repeated identical calls.
"""
import time
import json
import hashlib
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

class CachePlugin(BasePlugin):
    """Plugin for caching LLM and tool responses."""
    
    def __init__(self, ttl_s: int = 600):
        super().__init__(name="cache")
        self.ttl = ttl_s
        self._store = {}
        self._hits = 0
        self._misses = 0
    
    def _key(self, obj) -> str:
        """Generate cache key from object."""
        try:
            # Convert to JSON string and hash
            json_str = json.dumps(obj, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except Exception:
            # Fallback to string representation
            return hashlib.sha256(str(obj).encode()).hexdigest()
    
    async def before_model_callback(self, *, callback_context, llm_request):
        """Check cache before model call."""
        try:
            # Create cache key from request
            request_data = llm_request.model_dump() if hasattr(llm_request, 'model_dump') else str(llm_request)
            cache_key = self._key(request_data)
            
            # Check cache
            cached_entry = self._store.get(cache_key)
            if cached_entry and time.time() - cached_entry["timestamp"] < self.ttl:
                self._hits += 1
                logger.debug(f"[cache] Model cache HIT for key: {cache_key[:8]}...")
                return cached_entry["response"]  # Return cached LlmResponse
            
            self._misses += 1
            logger.debug(f"[cache] Model cache MISS for key: {cache_key[:8]}...")
            
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
        
        return None  # No cache hit, proceed with call
    
    async def after_model_callback(self, *, callback_context, llm_request, llm_response):
        """Cache model response."""
        try:
            # Create cache key from request
            request_data = llm_request.model_dump() if hasattr(llm_request, 'model_dump') else str(llm_request)
            cache_key = self._key(request_data)
            
            # Store response
            self._store[cache_key] = {
                "timestamp": time.time(),
                "response": llm_response
            }
            
            logger.debug(f"[cache] Model response cached for key: {cache_key[:8]}...")
            
        except Exception as e:
            logger.warning(f"Cache store failed: {e}")
    
    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        """Check cache before tool call."""
        try:
            # Create cache key from tool and args
            cache_data = {
                "tool": tool.name,
                "args": tool_args
            }
            cache_key = self._key(cache_data)
            
            # Check cache in tool context state
            cached_result = tool_context.state.get(f"cache:{cache_key}")
            if cached_result:
                self._hits += 1
                logger.debug(f"[cache] Tool cache HIT for {tool.name}")
                return cached_result
            
            self._misses += 1
            logger.debug(f"[cache] Tool cache MISS for {tool.name}")
            
        except Exception as e:
            logger.warning(f"Tool cache check failed: {e}")
        
        return None  # No cache hit, proceed with call
    
    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        """Cache tool response (store only serializable/safe form)."""
        try:
            import inspect
            # Create cache key from tool and args
            cache_data = {
                "tool": tool.name,
                "args": tool_args
            }
            cache_key = self._key(cache_data)

            # Sanitize result to avoid storing non-serializable objects (e.g., async generators)
            safe_value = None
            try:
                if inspect.isasyncgen(result) or inspect.isgenerator(result):
                    safe_value = "[non-serializable: generator]"
                else:
                    # Try JSON sanitize
                    safe_value = json.loads(json.dumps(result, default=str))
            except Exception:
                try:
                    safe_value = str(result)
                except Exception:
                    safe_value = "[unavailable]"

            # Store sanitized result in tool context state
            tool_context.state[f"cache:{cache_key}"] = safe_value

            logger.debug(f"[cache] Tool result cached for {tool.name}")

        except Exception as e:
            logger.warning(f"Tool cache store failed: {e}")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "entries": len(self._store),
            "ttl_seconds": self.ttl
        }
    
    def clear_cache(self):
        """Clear all cached entries."""
        self._store.clear()
        self._hits = 0
        self._misses = 0
        logger.info("[cache] Cache cleared")
