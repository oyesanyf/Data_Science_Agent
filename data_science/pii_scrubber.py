"""
Strong PII and secret scrubbing for logs.
"""
import re
from typing import List, Tuple, Pattern

# Comprehensive patterns for secrets and PII
_SECRET_PATTERNS: List[Tuple[Pattern, str]] = [
    # OpenAI API keys
    (re.compile(r'\bsk-[A-Za-z0-9]{20,}\b'), 'sk-***'),
    
    # Google API keys
    (re.compile(r'\bAIza[0-9A-Za-z\-_]{10,}\b'), 'A***'),
    
    # Bearer tokens
    (re.compile(r'\bBearer\s+[A-Za-z0-9\.\-_]{10,}\b', re.I), 'Bearer ***'),
    
    # JWT tokens
    (re.compile(r'\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b'), 'JWT***'),
    
    # AWS credentials
    (re.compile(r'\b(AKIA|ASIA)[A-Z0-9]{16}\b'), 'AWS***'),
    
    # Generic API keys and secrets
    (re.compile(r'(?i)(authorization|api[-_ ]?key|secret|token|password|passwd)\s*[:=]\s*\S+'), r'\1=***'),
    
    # Social Security Numbers
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 'SSN***'),
    
    # Credit card numbers (basic pattern)
    (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), 'CC***'),
    
    # Email addresses (partial redaction)
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '***@***.***'),
    
    # Phone numbers
    (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), 'PHONE***'),
    
    # IP addresses (private ranges)
    (re.compile(r'\b(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)\d{1,3}\.\d{1,3}\b'), 'IP***'),
    
    # Database connection strings
    (re.compile(r'(?i)(postgresql|mysql|mongodb)://[^:\s]+:[^@\s]+@'), 'DB://***:***@'),
    
    # Redis URLs
    (re.compile(r'redis://[^:\s]+:[^@\s]+@'), 'redis://***:***@'),
    
    # Generic URLs with credentials
    (re.compile(r'https?://[^:\s]+:[^@\s]+@'), 'https://***:***@'),
    
    # Base64 encoded secrets (long strings)
    (re.compile(r'\b[A-Za-z0-9+/]{40,}={0,2}\b'), 'B64***'),
    
    # UUIDs (might contain sensitive data)
    (re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I), 'UUID***'),
    
    # Session IDs
    (re.compile(r'\bsession[_-]?id\s*[:=]\s*\S+', re.I), 'session_id=***'),
    
    # Cookies
    (re.compile(r'\bcookie\s*[:=]\s*\S+', re.I), 'cookie=***'),
]

def sanitize_for_logs(msg: str, max_length: int = 500) -> str:
    """
    Sanitize message for logging by removing secrets and PII.
    
    Args:
        msg: Message to sanitize
        max_length: Maximum length of sanitized message
        
    Returns:
        Sanitized message safe for logging
    """
    try:
        # Normalize whitespace
        msg = msg.replace("\r", " ").replace("\n", " ")
        
        # Apply all sanitization patterns
        for pattern, replacement in _SECRET_PATTERNS:
            msg = pattern.sub(replacement, msg)
        
        # Truncate if too long
        if len(msg) > max_length:
            msg = msg[:max_length] + "..."
            
    except Exception:
        # If sanitization fails, return a safe fallback
        msg = "***SANITIZATION_ERROR***"
    
    return msg

def is_sensitive_data(text: str) -> bool:
    """
    Check if text contains sensitive data patterns.
    
    Args:
        text: Text to check
        
    Returns:
        True if sensitive data detected
    """
    try:
        for pattern, _ in _SECRET_PATTERNS:
            if pattern.search(text):
                return True
    except Exception:
        pass
    
    return False

def get_sanitization_stats() -> dict:
    """
    Get statistics about sanitization patterns.
    
    Returns:
        Dictionary with pattern counts and types
    """
    return {
        "total_patterns": len(_SECRET_PATTERNS),
        "pattern_types": [
            "OpenAI API keys", "Google API keys", "Bearer tokens", "JWT tokens",
            "AWS credentials", "Generic secrets", "SSN", "Credit cards",
            "Email addresses", "Phone numbers", "IP addresses", "Database URLs",
            "Redis URLs", "Generic URLs", "Base64", "UUIDs", "Session IDs", "Cookies"
        ]
    }
