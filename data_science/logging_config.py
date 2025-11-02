"""
Centralized logging configuration with rotation for the Data Science Agent.

Features:
- Rotating file handlers (10MB per file, keep 5 backups)
- Separate logs for agent, tools, and errors
- Console output for important messages
- Automatic cleanup of old logs
"""

import logging
import os
import json
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

# Create logs directory under the package folder
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
AGENT_LOG = LOGS_DIR / "agent.log"  # Single consolidated agent log (includes console output)
TOOLS_LOG = LOGS_DIR / "tools.log"
ERROR_LOG = LOGS_DIR / "errors.log"
DEBUG_LOG = LOGS_DIR / "debug.log"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotation settings
MAX_BYTES = 10 * 1024 * 1024  # 10MB per file
BACKUP_COUNT = 5  # Keep 5 backup files

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        try:
            # Base log data
            log_data = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            
            # Add exception info if present
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            
            # Add extra fields if available
            if self.include_extra:
                for key, value in record.__dict__.items():
                    if key not in {
                        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                        'filename', 'module', 'lineno', 'funcName', 'created',
                        'msecs', 'relativeCreated', 'thread', 'threadName',
                        'processName', 'process', 'getMessage', 'exc_info',
                        'exc_text', 'stack_info'
                    }:
                        log_data[key] = value
            
            return json.dumps(log_data, default=str)
            
        except Exception as e:
            # Fallback to simple format if JSON fails
            return f"{record.levelname}: {record.getMessage()}"

class SanitizedFormatter(logging.Formatter):
    """Formatter that sanitizes logs for PII/secrets."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from .pii_scrubber import sanitize_for_logs
            self.sanitize = sanitize_for_logs
        except ImportError:
            # Fallback if pii_scrubber is not available
            try:
                from pii_scrubber import sanitize_for_logs
                self.sanitize = sanitize_for_logs
            except ImportError:
                # No sanitization available, just return as-is
                self.sanitize = lambda x: x
    
    def format(self, record: logging.LogRecord) -> str:
        """Format and sanitize log record."""
        # Get the formatted message
        msg = super().format(record)
        # Sanitize it
        return self.sanitize(msg)


def setup_logger(
    name: str,
    log_file: Path,
    level: int = logging.INFO,
    console: bool = False,
    json_format: bool = False,
    sanitize: bool = True
) -> logging.Logger:
    """
    Set up a logger with rotating file handler.
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level
        console: Whether to also log to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # Choose formatter based on options
    if json_format:
        file_formatter = JSONFormatter()
    elif sanitize:
        file_formatter = SanitizedFormatter(LOG_FORMAT, DATE_FORMAT)
    else:
        file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_agent_logger() -> logging.Logger:
    """Get the main agent logger (console output goes to agent.log)."""
    logger = setup_logger("agent", AGENT_LOG, logging.DEBUG, console=True)
    
    return logger


def get_tools_logger() -> logging.Logger:
    """Get the tools execution logger."""
    # CRITICAL FIX: Also log to agent.log so all logs are in one place
    tools_logger = setup_logger("tools", TOOLS_LOG, logging.DEBUG, console=False)
    
    # Add handler to also write to agent.log
    agent_handler = RotatingFileHandler(
        AGENT_LOG,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    agent_handler.setLevel(logging.DEBUG)
    agent_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    tools_logger.addHandler(agent_handler)
    
    return tools_logger


def get_error_logger() -> logging.Logger:
    """Get the error logger."""
    # CRITICAL FIX: Also log to agent.log so all logs are in one place
    error_logger = setup_logger("errors", ERROR_LOG, logging.ERROR, console=True)
    
    # Add handler to also write to agent.log
    agent_handler = RotatingFileHandler(
        AGENT_LOG,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    agent_handler.setLevel(logging.ERROR)
    agent_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    error_logger.addHandler(agent_handler)
    
    return error_logger


def get_debug_logger() -> logging.Logger:
    """Get the debug logger."""
    return setup_logger("debug", DEBUG_LOG, logging.DEBUG, console=False)


def log_startup_info():
    """Log startup information."""
    # CRITICAL: Configure root logger to capture ALL logs and write to agent.log
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Add agent.log handler to root logger if not already present
    agent_log_exists = any(
        isinstance(h, RotatingFileHandler) and str(AGENT_LOG) in str(h.baseFilename)
        for h in root_logger.handlers
    )
    
    if not agent_log_exists:
        root_handler = RotatingFileHandler(
            AGENT_LOG,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        root_handler.setLevel(logging.DEBUG)
        root_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        root_logger.addHandler(root_handler)
    
    agent_logger = get_agent_logger()
    agent_logger.info("=" * 70)
    agent_logger.info("DATA SCIENCE AGENT STARTING")
    agent_logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    agent_logger.info(f"Logs directory: {LOGS_DIR.absolute()}")
    agent_logger.info(f"Log level: DEBUG (detailed logging enabled)")
    agent_logger.info(f"✅ ALL LOGS CONSOLIDATED: agent.log includes tools, errors, and console output")
    agent_logger.info(f"   - tools.log: Tool execution logs (also in agent.log)")
    agent_logger.info(f"   - errors.log: Error logs only (also in agent.log)")
    agent_logger.info(f"   - ROOT LOGGER configured to capture all Python logging")
    agent_logger.info(f"Log rotation: {MAX_BYTES // (1024*1024)}MB per file, {BACKUP_COUNT} backups")
    agent_logger.info("=" * 70)
    agent_logger.debug("Debug logging is active - all agent operations will be logged in detail")


def log_tool_execution(tool_name: str, params: dict, success: bool, duration: float = None):
    """
    Log tool execution details.
    
    Args:
        tool_name: Name of the tool
        params: Tool parameters (will be sanitized)
        success: Whether execution succeeded
        duration: Execution time in seconds
    """
    tools_logger = get_tools_logger()
    
    # Sanitize params (remove large data)
    safe_params = {}
    for key, value in params.items():
        if isinstance(value, (str, int, float, bool, type(None))):
            safe_params[key] = value
        elif isinstance(value, (list, tuple)) and len(value) < 10:
            safe_params[key] = value
        else:
            safe_params[key] = f"<{type(value).__name__}>"
    
    status = "SUCCESS" if success else "FAILED"
    duration_str = f" ({duration:.2f}s)" if duration else ""
    
    tools_logger.info(f"[{status}] {tool_name}{duration_str}")
    tools_logger.debug(f"Parameters: {safe_params}")


def log_error(error: Exception, context: str = None):
    """
    Log an error with context.
    
    Args:
        error: The exception that occurred
        context: Additional context about where/why the error occurred
    """
    error_logger = get_error_logger()
    
    if context:
        error_logger.error(f"Context: {context}")
    
    error_logger.error(f"{type(error).__name__}: {str(error)}", exc_info=True)


def cleanup_old_logs(days: int = 30):
    """
    Clean up log files older than specified days.
    
    Args:
        days: Delete logs older than this many days
    """
    import time
    
    cutoff_time = time.time() - (days * 86400)
    deleted_count = 0
    
    for log_file in LOGS_DIR.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete old log {log_file}: {e}")
    
    if deleted_count > 0:
        agent_logger = get_agent_logger()
        agent_logger.info(f"Cleaned up {deleted_count} old log files (older than {days} days)")


# Initialize logging on import
if __name__ != "__main__":
    log_startup_info()
    cleanup_old_logs()

