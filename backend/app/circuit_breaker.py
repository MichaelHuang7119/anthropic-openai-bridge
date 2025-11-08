"""
Circuit breaker implementation for fault tolerance and resilience.
Provides automatic failure detection and recovery for providers.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any, Optional, Dict
from .config import config

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for provider failure handling."""

    def __init__(
        self,
        provider_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            provider_name: Name of the provider
            failure_threshold: Number of failures to open circuit
            recovery_timeout: Time in seconds to wait before half-open
            expected_exception: Exception type that triggers failure
        """
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0

        # State change timestamps
        self.state_history: list = []

    def _record_state_change(self, new_state: CircuitState):
        """Record state change in history."""
        self.state = new_state
        self.state_history.append({
            "state": new_state.value,
            "timestamp": datetime.now(),
            "failure_count": self.failure_count
        })

    def _can_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return datetime.now() - self.last_failure_time >= timedelta(seconds=self.recovery_timeout)

    def _on_success(self):
        """Handle successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            # If we've had enough successes, close the circuit
            if self.success_count >= 3:  # Require 3 consecutive successes
                self.failure_count = 0
                self._record_state_change(CircuitState.CLOSED)
                logger.info(f"Circuit breaker CLOSED for provider {self.provider_name} (recovered)")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.CLOSED:
            # Check if we've exceeded the threshold
            if self.failure_count >= self.failure_threshold:
                self._record_state_change(CircuitState.OPEN)
                logger.warning(
                    f"Circuit breaker OPEN for provider {self.provider_name} "
                    f"({self.failure_count} failures)"
                )
        elif self.state == CircuitState.HALF_OPEN:
            # Failed during half-open testing, go back to open
            self._record_state_change(CircuitState.OPEN)
            logger.warning(
                f"Circuit breaker OPEN for provider {self.provider_name} "
                f"(failed during recovery test)"
            )

    async def call(
        self,
        func: Callable,
        *args,
        fallback_return: Any = None,
        **kwargs
    ) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Function arguments
            fallback_return: Value to return if circuit is open
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback value
        """
        # Check state
        if self.state == CircuitState.OPEN:
            # Check if we should try to reset
            if self._can_attempt_reset():
                self._record_state_change(CircuitState.HALF_OPEN)
                self.success_count = 0
                logger.info(
                    f"Circuit breaker HALF_OPEN for provider {self.provider_name} "
                    f"(attempting recovery)"
                )
            else:
                # Circuit is open and still in timeout period
                logger.debug(
                    f"Circuit breaker OPEN for provider {self.provider_name}, "
                    f"blocking request"
                )
                return fallback_return

        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
        except Exception as e:
            # Other exceptions also count as failures
            self._on_failure()
            raise

    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            Dictionary with circuit breaker information
        """
        return {
            "provider": self.provider_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "recovery_timeout": self.recovery_timeout,
            "can_attempt_reset": self._can_attempt_reset()
        }

    def get_state_history(self) -> list:
        """
        Get state change history.

        Returns:
            List of state changes
        """
        return self.state_history

    def reset(self):
        """Manually reset the circuit breaker."""
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self._record_state_change(CircuitState.CLOSED)
        logger.info(f"Circuit breaker manually reset for provider {self.provider_name}")


class CircuitBreakerRegistry:
    """Registry for managing circuit breakers for all providers."""

    def __init__(self):
        """Initialize registry."""
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(
        self,
        provider_name: str,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[int] = None
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker for a provider.

        Args:
            provider_name: Name of the provider
            failure_threshold: Override default threshold
            recovery_timeout: Override default timeout

        Returns:
            Circuit breaker instance
        """
        if provider_name not in self._breakers:
            # Get default values from config
            cb_config = config.app_config.circuit_breaker
            failure_threshold = failure_threshold or cb_config.failure_threshold
            recovery_timeout = recovery_timeout or cb_config.recovery_timeout

            self._breakers[provider_name] = CircuitBreaker(
                provider_name=provider_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )

        return self._breakers[provider_name]

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get states of all circuit breakers.

        Returns:
            Dictionary mapping provider names to states
        """
        return {
            provider_name: breaker.get_state()
            for provider_name, breaker in self._breakers.items()
        }

    def reset_breaker(self, provider_name: str):
        """
        Reset circuit breaker for a provider.

        Args:
            provider_name: Name of the provider
        """
        if provider_name in self._breakers:
            self._breakers[provider_name].reset()

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()

    def remove_breaker(self, provider_name: str):
        """
        Remove circuit breaker for a provider.

        Args:
            provider_name: Name of the provider
        """
        self._breakers.pop(provider_name, None)

    def get_open_circuits(self) -> list:
        """
        Get list of providers with open circuits.

        Returns:
            List of provider names with open circuits
        """
        return [
            provider_name
            for provider_name, breaker in self._breakers.items()
            if breaker.state == CircuitState.OPEN
        ]

    def get_half_open_circuits(self) -> list:
        """
        Get list of providers with half-open circuits.

        Returns:
            List of provider names with half-open circuits
        """
        return [
            provider_name
            for provider_name, breaker in self._breakers.items()
            if breaker.state == CircuitState.HALF_OPEN
        ]


# Global registry instance
_breaker_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """
    Get or create global circuit breaker registry.

    Returns:
        CircuitBreakerRegistry instance
    """
    global _breaker_registry
    if _breaker_registry is None:
        _breaker_registry = CircuitBreakerRegistry()
    return _breaker_registry


async def with_circuit_breaker(
    provider_name: str,
    func: Callable,
    *args,
    fallback_return: Any = None,
    **kwargs
) -> Any:
    """
    Execute function with circuit breaker protection.

    Args:
        provider_name: Name of the provider
        func: Function to execute
        *args: Function arguments
        fallback_return: Value to return if circuit is open
        **kwargs: Function keyword arguments

    Returns:
        Function result or fallback value
    """
    registry = get_circuit_breaker_registry()
    breaker = registry.get_breaker(provider_name)

    return await breaker.call(
        func,
        *args,
        fallback_return=fallback_return,
        **kwargs
    )
