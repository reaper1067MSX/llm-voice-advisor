"""Middleware and Interceptor abstractions for execution pipelines (Application Layer)."""

from typing import Any, Callable, Protocol
from abi_coach.domain.common.result import Result


class Middleware(Protocol):
    """Protocol for pipeline interceptors surrounding use case handler execution."""

    def handle(self, command: Any, next_handler: Callable[[Any], Result]) -> Result:
        """Intercept command execution before and after next_handler is called."""
        ...
