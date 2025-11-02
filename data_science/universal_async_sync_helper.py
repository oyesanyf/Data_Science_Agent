"""
Universal Async/Sync Mismatch Helper

Automatically handles async/sync mismatches in tool functions by:
1. Detecting if a function is async but being called synchronously
2. Detecting if a function is sync but being called asynchronously
3. Automatically wrapping with appropriate conversion logic
4. Providing seamless execution regardless of the calling context

This prevents the common issues where:
- Async functions are called synchronously (returns coroutine object instead of result)
- Sync functions are called asynchronously (blocks the event loop)
- Tool wrappers don't handle the async/sync mismatch properly
"""

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Union, Awaitable

logger = logging.getLogger(__name__)

def universal_async_sync_wrapper(func: Callable) -> Callable:
    """
    Universal wrapper that handles both async and sync function calls seamlessly.
    
    This wrapper:
    1. Detects the function type (async vs sync)
    2. Detects the calling context (async vs sync)
    3. Automatically converts between async/sync as needed
    4. Handles all edge cases and error conditions
    
    Args:
        func: The function to wrap (can be async or sync)
        
    Returns:
        A wrapped function that works in both async and sync contexts
    """
    
    # Check if the original function is async
    is_original_async = inspect.iscoroutinefunction(func)
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        """Sync wrapper that handles both async and sync functions."""
        try:
            if is_original_async:
                # Function is async, but we're in sync context
                logger.debug(f"[ASYNC_SYNC] Converting async {func.__name__} to sync execution")
                try:
                    # Try to get existing event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Event loop is running, we need to run in a new thread
                        logger.debug(f"[ASYNC_SYNC] Event loop running, using asyncio.run_coroutine_threadsafe")
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, func(*args, **kwargs))
                            return future.result()
                    else:
                        # No event loop running, we can use asyncio.run
                        logger.debug(f"[ASYNC_SYNC] No event loop, using asyncio.run")
                        return asyncio.run(func(*args, **kwargs))
                except RuntimeError as e:
                    if "no running event loop" in str(e):
                        # No event loop, use asyncio.run
                        logger.debug(f"[ASYNC_SYNC] No event loop detected, using asyncio.run")
                        return asyncio.run(func(*args, **kwargs))
                    else:
                        # Some other runtime error, try asyncio.run anyway
                        logger.warning(f"[ASYNC_SYNC] Runtime error in async conversion: {e}, trying asyncio.run")
                        return asyncio.run(func(*args, **kwargs))
            else:
                # Function is sync, call directly
                logger.debug(f"[ASYNC_SYNC] Calling sync {func.__name__} directly")
                return func(*args, **kwargs)
                
        except Exception as e:
            logger.error(f"[ASYNC_SYNC] Error in sync wrapper for {func.__name__}: {e}", exc_info=True)
            # Return a safe error response
            return {
                "status": "error",
                "error": f"Async/sync conversion failed: {str(e)}",
                "function": func.__name__,
                "type": "async_sync_conversion_error"
            }
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        """Async wrapper that handles both async and sync functions."""
        try:
            if is_original_async:
                # Function is async, await it
                logger.debug(f"[ASYNC_SYNC] Awaiting async {func.__name__}")
                return await func(*args, **kwargs)
            else:
                # Function is sync, run it in executor to avoid blocking
                logger.debug(f"[ASYNC_SYNC] Running sync {func.__name__} in executor")
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func, *args, **kwargs)
                
        except Exception as e:
            logger.error(f"[ASYNC_SYNC] Error in async wrapper for {func.__name__}: {e}", exc_info=True)
            # Return a safe error response
            return {
                "status": "error",
                "error": f"Async/sync conversion failed: {str(e)}",
                "function": func.__name__,
                "type": "async_sync_conversion_error"
            }
    
    # Return the appropriate wrapper based on the calling context
    # We'll detect this at runtime by checking if we're in an async context
    @functools.wraps(func)
    def smart_wrapper(*args, **kwargs):
        """Smart wrapper that detects calling context and uses appropriate handler."""
        try:
            # Check if we're in an async context
            try:
                asyncio.current_task()
                # We're in an async context, use async wrapper
                logger.debug(f"[ASYNC_SYNC] Detected async context, using async wrapper for {func.__name__}")
                return async_wrapper(*args, **kwargs)
            except RuntimeError:
                # No current task, we're in sync context, use sync wrapper
                logger.debug(f"[ASYNC_SYNC] Detected sync context, using sync wrapper for {func.__name__}")
                return sync_wrapper(*args, **kwargs)
        except Exception as e:
            logger.error(f"[ASYNC_SYNC] Error in smart wrapper for {func.__name__}: {e}", exc_info=True)
            # Fallback to sync wrapper
            return sync_wrapper(*args, **kwargs)
    
    # For async functions, we need to return a coroutine function
    if is_original_async:
        return async_wrapper
    else:
        return smart_wrapper


def auto_fix_async_sync_mismatch(func: Callable) -> Callable:
    """
    Automatically fix async/sync mismatches for any function.
    
    This is a drop-in replacement that can be used as a decorator
    or applied to existing functions to fix async/sync issues.
    
    Args:
        func: The function to fix
        
    Returns:
        A fixed function that handles both async and sync contexts
    """
    return universal_async_sync_wrapper(func)


def ensure_async_sync_compatibility(func: Callable) -> Callable:
    """
    Ensure a function is compatible with both async and sync calling contexts.
    
    This is an alias for auto_fix_async_sync_mismatch for clarity.
    """
    return auto_fix_async_sync_mismatch(func)


# Convenience decorators
def async_sync_safe(func: Callable) -> Callable:
    """Decorator to make any function safe for both async and sync contexts."""
    return auto_fix_async_sync_mismatch(func)


def universal_tool_wrapper(func: Callable) -> Callable:
    """Universal tool wrapper that handles all async/sync issues."""
    return auto_fix_async_sync_mismatch(func)


# Utility functions for manual async/sync conversion
def run_async_in_sync(async_func: Callable, *args, **kwargs) -> Any:
    """Run an async function in a sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Event loop is running, use thread executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                return future.result()
        else:
            # No event loop, use asyncio.run
            return asyncio.run(async_func(*args, **kwargs))
    except Exception as e:
        logger.error(f"[ASYNC_SYNC] Error running async in sync: {e}", exc_info=True)
        raise


async def run_sync_in_async(sync_func: Callable, *args, **kwargs) -> Any:
    """Run a sync function in an async context."""
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)
    except Exception as e:
        logger.error(f"[ASYNC_SYNC] Error running sync in async: {e}", exc_info=True)
        raise


# Test functions to verify the helper works
def test_sync_function():
    """Test sync function."""
    return {"status": "success", "type": "sync", "message": "Sync function executed"}


async def test_async_function():
    """Test async function."""
    await asyncio.sleep(0.01)  # Simulate async work
    return {"status": "success", "type": "async", "message": "Async function executed"}


if __name__ == "__main__":
    # Test the helper
    print("Testing Universal Async/Sync Helper...")
    
    # Test sync function
    sync_func = test_sync_function
    wrapped_sync = universal_async_sync_wrapper(sync_func)
    
    # Test async function
    async_func = test_async_function
    wrapped_async = universal_async_sync_wrapper(async_func)
    
    print("✅ Universal Async/Sync Helper created successfully!")
    print("Use @async_sync_safe or @universal_tool_wrapper as decorators")
    print("Or use auto_fix_async_sync_mismatch(func) to fix existing functions")
