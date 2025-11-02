"""
Telemetry, timeouts, and health probes for observability.
"""
import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Configuration
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "300"))  # 5 minutes
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"

@dataclass
class TelemetryMetrics:
    """Telemetry metrics for monitoring."""
    agent_llm_latency_ms: float = 0.0
    agent_rate_limit_hits: int = 0
    agent_ctx_reduction_level: int = 0
    uploads_bytes_total: int = 0
    tool_executions_total: int = 0
    tool_execution_errors: int = 0
    circuit_breaker_opens: int = 0
    circuit_breaker_closes: int = 0
    last_health_check: Optional[str] = None
    health_check_failures: int = 0

class TelemetryCollector:
    """Collects and manages telemetry metrics."""
    
    def __init__(self):
        self.metrics = TelemetryMetrics()
        self.start_time = time.time()
        self.last_health_check = None
        
    def record_llm_latency(self, latency_ms: float):
        """Record LLM latency."""
        self.metrics.agent_llm_latency_ms = latency_ms
        
    def record_rate_limit_hit(self):
        """Record rate limit hit."""
        self.metrics.agent_rate_limit_hits += 1
        
    def record_context_reduction(self, level: int):
        """Record context reduction level."""
        self.metrics.agent_ctx_reduction_level = level
        
    def record_upload(self, bytes_count: int):
        """Record file upload."""
        self.metrics.uploads_bytes_total += bytes_count
        
    def record_tool_execution(self, success: bool = True):
        """Record tool execution."""
        self.metrics.tool_executions_total += 1
        if not success:
            self.metrics.tool_execution_errors += 1
            
    def record_circuit_breaker_open(self):
        """Record circuit breaker opening."""
        self.metrics.circuit_breaker_opens += 1
        
    def record_circuit_breaker_close(self):
        """Record circuit breaker closing."""
        self.metrics.circuit_breaker_closes += 1
        
    def record_health_check(self, success: bool):
        """Record health check result."""
        self.last_health_check = datetime.now().isoformat()
        if not success:
            self.metrics.health_check_failures += 1
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        uptime_seconds = time.time() - self.start_time
        return {
            **asdict(self.metrics),
            "uptime_seconds": uptime_seconds,
            "uptime_hours": uptime_seconds / 3600,
            "tool_success_rate": (
                (self.metrics.tool_executions_total - self.metrics.tool_execution_errors) 
                / max(1, self.metrics.tool_executions_total)
            ),
            "last_health_check": self.last_health_check
        }

# Global telemetry collector
_telemetry = TelemetryCollector()

def get_telemetry() -> TelemetryCollector:
    """Get the global telemetry collector."""
    return _telemetry

async def probe_llm_health(
    timeout_seconds: float = 5.0,
    model: str = "gpt-3.5-turbo"
) -> bool:
    """
    Probe LLM health with timeout.
    
    Args:
        timeout_seconds: Timeout for health check
        model: Model to test
        
    Returns:
        True if healthy, False otherwise
    """
    try:
        from litellm import acompletion
        
        start_time = time.time()
        
        # Simple health check request
        response = await asyncio.wait_for(
            acompletion(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                temperature=0
            ),
            timeout=timeout_seconds
        )
        
        latency_ms = (time.time() - start_time) * 1000
        _telemetry.record_llm_latency(latency_ms)
        
        # Check if response is valid
        if response and response.choices:
            _telemetry.record_health_check(True)
            logger.info(f"[OK] LLM health check passed ({latency_ms:.1f}ms)")
            return True
        
        _telemetry.record_health_check(False)
        logger.warning("[WARNING] LLM health check failed: Empty response")
        return False
        
    except asyncio.TimeoutError:
        _telemetry.record_health_check(False)
        logger.warning(f"[WARNING] LLM health check timeout ({timeout_seconds}s)")
        return False
        
    except Exception as e:
        _telemetry.record_health_check(False)
        logger.warning(f"[WARNING] LLM health check failed: {str(e)}")
        return False

async def periodic_health_check():
    """Run periodic health checks."""
    while True:
        try:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            
            # Check LLM health
            is_healthy = await probe_llm_health()
            
            if not is_healthy:
                logger.warning("[ALERT] Health check failed - LLM may be degraded")
            
            # Log metrics
            if METRICS_ENABLED:
                metrics = _telemetry.get_metrics()
                logger.info(f" Telemetry: {metrics}")
                
        except Exception as e:
            logger.error(f"Health check error: {e}")

def start_telemetry():
    """Start telemetry collection."""
    if METRICS_ENABLED:
        logger.info(" Telemetry enabled")
        # Start periodic health checks in background
        asyncio.create_task(periodic_health_check())
    else:
        logger.info(" Telemetry disabled")

def emit_metrics():
    """Emit current metrics."""
    if not METRICS_ENABLED:
        return
        
    metrics = _telemetry.get_metrics()
    
    # Log structured metrics
    logger.info(f" METRICS: {metrics}")
    
    # Could also send to external monitoring system
    # send_to_monitoring_system(metrics)

def check_slos() -> Dict[str, bool]:
    """
    Check Service Level Objectives.
    
    Returns:
        Dictionary of SLO checks
    """
    metrics = _telemetry.get_metrics()
    
    slos = {
        "llm_latency_ok": metrics["agent_llm_latency_ms"] < 5000,  # < 5 seconds
        "tool_success_rate_ok": metrics["tool_success_rate"] > 0.95,  # > 95%
        "health_check_ok": metrics["health_check_failures"] < 3,  # < 3 failures
        "uptime_ok": metrics["uptime_hours"] > 0.1,  # > 6 minutes
    }
    
    return slos
