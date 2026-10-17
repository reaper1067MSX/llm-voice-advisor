"""Circuit Breaker resilience pattern implementation for LLM Providers."""

from enum import Enum
import threading
import time
from typing import Optional


class CircuitState(str, Enum):
    """States of a Circuit Breaker."""

    CLOSED = "CLOSED"        # Operación normal: el tráfico fluye
    OPEN = "OPEN"            # Circuito abierto: peticiones fallan inmediatamente (Fail-Fast)
    HALF_OPEN = "HALF_OPEN"  # Enfriamiento: permite una petición de prueba para verificar recuperación


class CircuitBreaker:
    """Thread-safe in-process Circuit Breaker (Michael Nygard / Release It! pattern)."""

    def __init__(
        self,
        name: str = "llm-provider",
        failure_threshold: int = 2,
        recovery_timeout_sec: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        """Check if a request is permitted to execute according to circuit state."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                now = time.time()
                if now - self.last_failure_time >= self.recovery_timeout_sec:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                return True

            return False

    def record_success(self) -> None:
        """Record a successful execution, closing the circuit if open or half-open."""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record an execution failure, opening the circuit if threshold is reached."""
        with self._lock:
            self.last_failure_time = time.time()
            self.failure_count += 1

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    @property
    def is_open(self) -> bool:
        """Check if the circuit is currently open (failing fast)."""
        with self._lock:
            return self.state == CircuitState.OPEN

    def get_state(self) -> CircuitState:
        """Return the current circuit state."""
        with self._lock:
            return self.state
