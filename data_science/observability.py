"""
Observability utilities: structured logging, metrics, and tracing.

Provides JSON logging, operation timing, and audit trails.
"""
from __future__ import annotations

import time
import logging
import json
import hashlib
import functools
from typing import Any, Optional, Callable, Dict
from contextlib import contextmanager

from .config import Config


# ==================== STRUCTURED LOGGING ====================

class StructuredLogger:
    """Structured JSON logger for production observability."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    def _log(self, level: str, message: str, **kwargs):
        """Log structured message with context."""
        if Config.LOG_FORMAT == "json":
            log_entry = {
                "timestamp": time.time(),
                "level": level,
                "message": message,
                **kwargs
            }
            self.logger.log(
                getattr(logging, level),
                json.dumps(log_entry, default=str)
            )
        else:
            # Text format with key=value pairs
            context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
            self.logger.log(
                getattr(logging, level),
                f"{message} {context}" if context else message
            )
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)


# ==================== OPERATION TIMING ====================

@contextmanager
def timed_operation(operation_name: str, logger: Optional[StructuredLogger] = None):
    """
    Context manager to time operations and log results.
    
    Usage:
        with timed_operation("upload_processing", logger):
            # ... do work ...
            pass
    """
    start = time.time()
    error = None
    
    try:
        yield
    except Exception as e:
        error = str(e)
        raise
    finally:
        duration = time.time() - start
        if logger:
            logger.info(
                f"Operation completed: {operation_name}",
                operation=operation_name,
                duration_seconds=round(duration, 3),
                status="error" if error else "success",
                error=error
            )


def timed(operation_name: Optional[str] = None):
    """
    Decorator to time function execution and log.
    
    Usage:
        @timed("process_csv")
        async def process_csv(path: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        logger = StructuredLogger(func.__module__)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with timed_operation(op_name, logger):
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with timed_operation(op_name, logger):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ==================== AUDIT TRAIL ====================

class AuditLogger:
    """Audit logger for sensitive operations."""
    
    def __init__(self):
        self.logger = StructuredLogger("audit")
    
    def log_upload(
        self,
        user_id: Optional[str],
        filename: str,
        size_bytes: int,
        mime_type: str,
        file_hash: str,
        status: str,
        error: Optional[str] = None
    ):
        """Log file upload event."""
        self.logger.info(
            "File upload",
            event="upload",
            user_id_hash=self._hash_user_id(user_id) if user_id else None,
            filename_sanitized=self._sanitize_filename(filename),
            size_bytes=size_bytes,
            mime_type=mime_type,
            file_sha256=file_hash[:16],  # First 16 chars only
            status=status,
            error=error
        )
    
    def log_tool_execution(
        self,
        tool_name: str,
        user_id: Optional[str],
        parameters: Dict[str, Any],
        duration_seconds: float,
        status: str,
        error: Optional[str] = None
    ):
        """Log tool execution event."""
        self.logger.info(
            f"Tool executed: {tool_name}",
            event="tool_execution",
            tool_name=tool_name,
            user_id_hash=self._hash_user_id(user_id) if user_id else None,
            parameters_count=len(parameters),
            duration_seconds=round(duration_seconds, 3),
            status=status,
            error=error
        )
    
    def log_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: Optional[float],
        duration_seconds: float,
        status: str
    ):
        """Log LLM API call."""
        self.logger.info(
            f"LLM call: {model}",
            event="llm_call",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=round(cost_usd, 6) if cost_usd else None,
            duration_seconds=round(duration_seconds, 3),
            status=status
        )
    
    def log_automl_run(
        self,
        tool_name: str,
        dataset_rows: int,
        dataset_cols: int,
        target_column: str,
        time_limit_seconds: int,
        actual_duration_seconds: float,
        models_trained: int,
        best_score: Optional[float],
        status: str
    ):
        """Log AutoML training run."""
        self.logger.info(
            f"AutoML run: {tool_name}",
            event="automl_run",
            tool_name=tool_name,
            dataset_shape=f"{dataset_rows}x{dataset_cols}",
            target_column=target_column,
            time_limit_seconds=time_limit_seconds,
            actual_duration_seconds=round(actual_duration_seconds, 3),
            models_trained=models_trained,
            best_score=round(best_score, 4) if best_score else None,
            status=status
        )
    
    @staticmethod
    def _hash_user_id(user_id: str) -> str:
        """Hash user ID for privacy."""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename for logging (remove sensitive info)."""
        import os
        # Return just the extension and first few chars
        name, ext = os.path.splitext(filename)
        if len(name) > 8:
            return f"{name[:8]}...{ext}"
        return filename


# ==================== METRICS COLLECTOR ====================

class MetricsCollector:
    """Simple in-memory metrics collector."""
    
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = {}
    
    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter."""
        self.counters[metric_name] = self.counters.get(metric_name, 0) + value
    
    def set_gauge(self, metric_name: str, value: float):
        """Set a gauge value."""
        self.gauges[metric_name] = value
    
    def record(self, metric_name: str, value: float):
        """Record a value in histogram."""
        if metric_name not in self.histograms:
            self.histograms[metric_name] = []
        self.histograms[metric_name].append(value)
        # Keep only last 1000 values
        if len(self.histograms[metric_name]) > 1000:
            self.histograms[metric_name] = self.histograms[metric_name][-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        return {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "histograms": {
                k: {
                    "count": len(v),
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                    "avg": sum(v) / len(v) if v else 0
                }
                for k, v in self.histograms.items()
            }
        }


# ==================== GLOBAL INSTANCES ====================

# Global singletons for easy access
audit_logger = AuditLogger()
metrics = MetricsCollector()


# ==================== COST TRACKING ====================

def estimate_llm_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate LLM API cost in USD.
    
    Prices as of 2025 (update regularly):
    - GPT-4o: $2.50/1M input, $10.00/1M output
    - GPT-4o-mini: $0.15/1M input, $0.60/1M output
    - Gemini 2.0 Flash: Free tier, then ~$0.075/1M
    """
    pricing = {
        "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
        "gemini-2.0-flash-exp": (0.075 / 1_000_000, 0.30 / 1_000_000),
    }
    
    model_lower = model.lower()
    for key, (input_price, output_price) in pricing.items():
        if key in model_lower:
            return (prompt_tokens * input_price) + (completion_tokens * output_price)
    
    # Default estimate
    return (prompt_tokens * 0.5 / 1_000_000) + (completion_tokens * 1.5 / 1_000_000)


# ==================== HELPERS ====================

def hash_file(file_path: str) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

