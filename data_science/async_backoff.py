"""
Async-aware backoff decorator that prevents event-loop stalls.
Replaces time.sleep with asyncio.sleep for async functions.
"""
import inspect
import asyncio
import time
from functools import wraps
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

def with_backoff(
    max_retries: int = 4,
    base_delay: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 30.0,
    jitter: float = 0.25
):
    """
    Decorator that adds exponential backoff with jitter to functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        factor: Multiplier for delay after each failure
        max_delay: Maximum delay cap in seconds
        jitter: Random jitter to prevent thundering herd
    """
    def decorator(fn: Callable) -> Callable:
        async def _async_call(*args, **kwargs) -> Any:
            delay = base_delay
            for attempt in range(max_retries):
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    msg = str(e).lower()
                    retriable = any(x in msg for x in (
                        "rate limit", "too many requests", "429", 
                        "temporarily unavailable", "overloaded", 
                        "resource_exhausted", "quota", "503",
                        "context window exceeded", "timeout"
                    ))
                    
                    if attempt == max_retries - 1 or not retriable:
                        logger.error(f"Final attempt failed for {fn.__name__}: {e}")
                        raise
                    
                    # Calculate delay with jitter
                    actual_delay = min(delay, max_delay) + (jitter * (0.5 - time.time() % 1))
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {fn.__name__} in {actual_delay:.2f}s: {e}")
                    
                    await asyncio.sleep(actual_delay)
                    delay *= factor

        def _sync_call(*args, **kwargs) -> Any:
            delay = base_delay
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    msg = str(e).lower()
                    retriable = any(x in msg for x in (
                        "rate limit", "too many requests", "429",
                        "temporarily unavailable", "overloaded",
                        "resource_exhausted", "quota", "503",
                        "context window exceeded", "timeout"
                    ))
                    
                    if attempt == max_retries - 1 or not retriable:
                        logger.error(f"Final attempt failed for {fn.__name__}: {e}")
                        raise
                    
                    # Calculate delay with jitter
                    actual_delay = min(delay, max_delay) + (jitter * (0.5 - time.time() % 1))
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {fn.__name__} in {actual_delay:.2f}s: {e}")
                    
                    time.sleep(actual_delay)
                    delay *= factor

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(fn):
            return wraps(fn)(_async_call)
        else:
            return wraps(fn)(_sync_call)
    
    return decorator
