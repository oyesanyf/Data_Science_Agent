"""
Thread-Safe Circuit Breaker for Gemini API
Uses monotonic clock for reliable cooldown tracking.
"""

import time
import logging
from threading import Lock
from typing import Optional

from .large_data_config import CIRCUIT_BREAKER_THRESHOLD, CIRCUIT_BREAKER_COOLDOWN

logger = logging.getLogger(__name__)


class GeminiCircuitBreaker:
    """
    Thread-safe circuit breaker for Gemini API.
    
    States:
    - CLOSED: Normal operation, Gemini is healthy
    - OPEN: Too many failures, Gemini is unavailable
    - HALF_OPEN: Testing if Gemini recovered (implicit during readiness check)
    
    Features:
    - Thread-safe with explicit locking
    - Monotonic clock for reliable cooldown
    - Automatic recovery after cooldown period
    - Readiness ping before marking healthy
    """
    
    def __init__(
        self,
        failure_threshold: Optional[int] = None,
        cooldown_seconds: Optional[int] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            cooldown_seconds: Seconds to wait before attempting recovery
        """
        self._lock = Lock()
        self.failure_threshold = failure_threshold or CIRCUIT_BREAKER_THRESHOLD
        self.cooldown_seconds = cooldown_seconds or CIRCUIT_BREAKER_COOLDOWN
        
        # State tracking
        self.failure_count = 0
        self._opened_at: Optional[float] = None  # Monotonic timestamp
        self.is_open = False
        
        # Success tracking
        self.total_successes = 0
        self.total_failures = 0
        
        logger.info(
            f"Circuit Breaker initialized: "
            f"threshold={self.failure_threshold}, "
            f"cooldown={self.cooldown_seconds}s"
        )
    
    def record_failure(self, error: Optional[Exception] = None) -> None:
        """
        Record a failure and potentially open the circuit.
        
        Args:
            error: Optional exception that caused the failure
        """
        with self._lock:
            self.failure_count += 1
            self.total_failures += 1
            
            error_msg = f": {str(error)}" if error else ""
            
            if self.failure_count >= self.failure_threshold:
                if not self.is_open:
                    # Transition to OPEN state
                    self.is_open = True
                    self._opened_at = time.monotonic()
                    logger.warning(
                        f"[WARNING] Circuit breaker OPENED after {self.failure_count} failures{error_msg}. "
                        f"Cooldown: {self.cooldown_seconds}s"
                    )
                else:
                    logger.debug(f"Circuit breaker remains OPEN (failure count: {self.failure_count}){error_msg}")
            else:
                logger.warning(
                    f"Circuit breaker: Failure {self.failure_count}/{self.failure_threshold}{error_msg}"
                )
    
    def record_success(self) -> None:
        """
        Record a success and reset the circuit to CLOSED state.
        """
        with self._lock:
            prev_state = "OPEN" if self.is_open else "CLOSED"
            
            # Reset to healthy state
            self.failure_count = 0
            self.is_open = False
            self._opened_at = None
            self.total_successes += 1
            
            if prev_state == "OPEN":
                logger.info("[OK] Circuit breaker CLOSED (Gemini recovered)")
            else:
                logger.debug("Circuit breaker: Success recorded")
    
    def can_use_gemini(self) -> bool:
        """
        Check if Gemini can be used (circuit is CLOSED or cooldown expired).
        
        Returns:
            True if Gemini can be used, False otherwise
        """
        with self._lock:
            # Circuit is CLOSED - OK to use
            if not self.is_open:
                return True
            
            # Circuit is OPEN - check if cooldown expired
            if self._opened_at is None:
                # Opened but no timestamp? Safety fallback
                return False
            
            elapsed = time.monotonic() - self._opened_at
            
            if elapsed >= self.cooldown_seconds:
                # Cooldown expired - transition to HALF_OPEN (implicit)
                # Don't automatically close - wait for readiness ping
                logger.info(
                    f"Circuit breaker cooldown expired ({elapsed:.1f}s). "
                    f"Ready for health check."
                )
                # Reset failure count to allow ONE attempt
                self.failure_count = 0
                # Keep circuit open until explicit success
                return True
            
            # Still in cooldown
            remaining = self.cooldown_seconds - elapsed
            logger.debug(f"Circuit breaker OPEN (cooldown: {remaining:.1f}s remaining)")
            return False
    
    def force_open(self, reason: str = "Manual intervention") -> None:
        """
        Manually open the circuit (for testing or emergency).
        
        Args:
            reason: Reason for manual intervention
        """
        with self._lock:
            self.is_open = True
            self._opened_at = time.monotonic()
            self.failure_count = self.failure_threshold
            logger.warning(f"Circuit breaker manually OPENED: {reason}")
    
    def force_close(self, reason: str = "Manual intervention") -> None:
        """
        Manually close the circuit (for testing or recovery).
        
        Args:
            reason: Reason for manual intervention
        """
        with self._lock:
            self.is_open = False
            self._opened_at = None
            self.failure_count = 0
            logger.info(f"Circuit breaker manually CLOSED: {reason}")
    
    def get_stats(self) -> dict:
        """
        Get current circuit breaker statistics.
        
        Returns:
            Dictionary with stats
        """
        with self._lock:
            stats = {
                "state": "OPEN" if self.is_open else "CLOSED",
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "total_successes": self.total_successes,
                "total_failures": self.total_failures,
                "success_rate": (
                    round(100 * self.total_successes / (self.total_successes + self.total_failures), 2)
                    if (self.total_successes + self.total_failures) > 0
                    else 0
                )
            }
            
            if self.is_open and self._opened_at is not None:
                elapsed = time.monotonic() - self._opened_at
                stats["cooldown_elapsed_s"] = round(elapsed, 1)
                stats["cooldown_remaining_s"] = max(0, round(self.cooldown_seconds - elapsed, 1))
            
            return stats
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<GeminiCircuitBreaker "
            f"state={stats['state']} "
            f"failures={stats['failure_count']}/{stats['failure_threshold']} "
            f"success_rate={stats['success_rate']}%>"
        )


# Global singleton instance
_global_breaker: Optional[GeminiCircuitBreaker] = None


def get_circuit_breaker() -> GeminiCircuitBreaker:
    """Get or create the global circuit breaker instance."""
    global _global_breaker
    if _global_breaker is None:
        _global_breaker = GeminiCircuitBreaker()
    return _global_breaker


def reset_circuit_breaker() -> None:
    """Reset the global circuit breaker (useful for testing)."""
    global _global_breaker
    _global_breaker = None


# ============================================================================
# Readiness Ping (Test Gemini Health Before Marking Healthy)
# ============================================================================

async def ping_gemini_health(
    timeout_seconds: float = 5.0
) -> bool:
    """
    Ping Gemini API to check if it's healthy.
    
    Args:
        timeout_seconds: Timeout for the health check
    
    Returns:
        True if Gemini is healthy, False otherwise
    """
    try:
        import asyncio
        from litellm import acompletion
        
        # Tiny test request
        response = await asyncio.wait_for(
            acompletion(
                model="gemini/gemini-1.5-flash",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                temperature=0
            ),
            timeout=timeout_seconds
        )
        
        # Check if response is valid
        if response and response.choices:
            logger.info("[OK] Gemini health check: PASSED")
            return True
        
        logger.warning("[WARNING] Gemini health check: Empty response")
        return False
    
    except asyncio.TimeoutError:
        logger.warning(f"[WARNING] Gemini health check: TIMEOUT ({timeout_seconds}s)")
        return False
    
    except Exception as e:
        logger.warning(f"[WARNING] Gemini health check: FAILED - {str(e)}")
        return False


# ============================================================================
# Context Manager for Safe Gemini Usage
# ============================================================================

class GeminiCircuitBreakerContext:
    """
    Context manager for safe Gemini API usage with circuit breaker.
    
    Usage:
        async with GeminiCircuitBreakerContext() as can_use:
            if can_use:
                # Use Gemini
                result = await gemini_call()
            else:
                # Fallback to OpenAI
                result = await openai_call()
    """
    
    def __init__(self, breaker: Optional[GeminiCircuitBreaker] = None):
        self.breaker = breaker or get_circuit_breaker()
        self.can_use = False
    
    async def __aenter__(self):
        """Check if Gemini can be used."""
        self.can_use = self.breaker.can_use_gemini()
        
        if not self.can_use:
            logger.info("Circuit breaker OPEN - skipping Gemini, using fallback")
        
        return self.can_use
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Record success or failure based on exception."""
        if exc_type is None:
            # No exception - success
            if self.can_use:
                self.breaker.record_success()
        else:
            # Exception occurred - failure
            if self.can_use:
                self.breaker.record_failure(exc_val)
        
        # Don't suppress the exception
        return False


if __name__ == "__main__":
    # Test the circuit breaker
    breaker = GeminiCircuitBreaker(failure_threshold=3, cooldown_seconds=5)
    
    print("Initial state:", breaker.get_stats())
    
    # Simulate failures
    for i in range(5):
        print(f"\nFailure {i+1}:")
        breaker.record_failure()
        print(breaker.get_stats())
        print(f"Can use Gemini? {breaker.can_use_gemini()}")
    
    # Wait for cooldown
    print("\nWaiting 6 seconds for cooldown...")
    time.sleep(6)
    print(f"Can use Gemini? {breaker.can_use_gemini()}")
    
    # Record success
    print("\nRecording success:")
    breaker.record_success()
    print(breaker.get_stats())
    print(f"Can use Gemini? {breaker.can_use_gemini()}")

