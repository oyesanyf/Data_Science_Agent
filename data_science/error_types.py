"""
Specific error types for better error handling and triage.
"""
from typing import Optional, Dict, Any

class RateLimitError(Exception):
    """Rate limit exceeded error."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after

class ValidationError(Exception):
    """Data validation error."""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field

class ContextWindowError(Exception):
    """Context window exceeded error."""
    def __init__(self, message: str, token_count: Optional[int] = None):
        super().__init__(message)
        self.token_count = token_count

class CircuitBreakerError(Exception):
    """Circuit breaker is open."""
    def __init__(self, message: str, service: Optional[str] = None):
        super().__init__(message)
        self.service = service

class ToolExecutionError(Exception):
    """Tool execution failed."""
    def __init__(self, message: str, tool_name: Optional[str] = None):
        super().__init__(message)
        self.tool_name = tool_name

class FileProcessingError(Exception):
    """File processing error."""
    def __init__(self, message: str, file_path: Optional[str] = None):
        super().__init__(message)
        self.file_path = file_path

class ModelLoadingError(Exception):
    """Model loading error."""
    def __init__(self, message: str, model_path: Optional[str] = None):
        super().__init__(message)
        self.model_path = model_path

def categorize_error(error: Exception) -> Dict[str, Any]:
    """
    Categorize an error for better handling.
    
    Args:
        error: Exception to categorize
        
    Returns:
        Dictionary with error category and metadata
    """
    error_info = {
        "type": type(error).__name__,
        "message": str(error),
        "category": "unknown",
        "retriable": False,
        "unexpected": True
    }
    
    # Categorize known error types
    if isinstance(error, RateLimitError):
        error_info.update({
            "category": "rate_limit",
            "retriable": True,
            "unexpected": False,
            "retry_after": getattr(error, 'retry_after', None)
        })
    elif isinstance(error, ContextWindowError):
        error_info.update({
            "category": "context_window",
            "retriable": True,
            "unexpected": False,
            "token_count": getattr(error, 'token_count', None)
        })
    elif isinstance(error, CircuitBreakerError):
        error_info.update({
            "category": "circuit_breaker",
            "retriable": True,
            "unexpected": False,
            "service": getattr(error, 'service', None)
        })
    elif isinstance(error, ValidationError):
        error_info.update({
            "category": "validation",
            "retriable": False,
            "unexpected": False,
            "field": getattr(error, 'field', None)
        })
    elif isinstance(error, ToolExecutionError):
        error_info.update({
            "category": "tool_execution",
            "retriable": True,
            "unexpected": False,
            "tool_name": getattr(error, 'tool_name', None)
        })
    elif isinstance(error, FileProcessingError):
        error_info.update({
            "category": "file_processing",
            "retriable": False,
            "unexpected": False,
            "file_path": getattr(error, 'file_path', None)
        })
    elif isinstance(error, ModelLoadingError):
        error_info.update({
            "category": "model_loading",
            "retriable": True,
            "unexpected": False,
            "model_path": getattr(error, 'model_path', None)
        })
    
    return error_info

def is_retriable_error(error: Exception) -> bool:
    """
    Check if an error is retriable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is retriable
    """
    return categorize_error(error)["retriable"]

def is_unexpected_error(error: Exception) -> bool:
    """
    Check if an error is unexpected.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is unexpected
    """
    return categorize_error(error)["unexpected"]
