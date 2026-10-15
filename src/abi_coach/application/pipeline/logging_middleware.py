"""Logging and Telemetry Middleware (Application Layer)."""

import logging
import time
from typing import Any, Callable, List, Optional
from abi_coach.domain.common.result import Result

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """Measures latency, audits commands, and records result state."""

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        self.logger = logger_instance or logger
        self.last_latency_ms: float = 0.0

    def handle(self, command: Any, next_handler: Callable[[Any], Result]) -> Result:
        cmd_name = command.__class__.__name__
        start = time.perf_counter()
        self.logger.debug("Executing command: %s", cmd_name)

        result = next_handler(command)

        elapsed = (time.perf_counter() - start) * 1000
        self.last_latency_ms = elapsed

        status = "OK" if result.is_ok() else "FAIL"
        self.logger.debug(
            "Command %s finished with status %s in %.2f ms",
            cmd_name,
            status,
            elapsed,
        )
        return result
