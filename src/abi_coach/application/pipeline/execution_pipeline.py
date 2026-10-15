"""Execution Pipeline composing middlewares and use case handlers (Application Layer)."""

from typing import Any, Callable, List, Optional
from abi_coach.application.pipeline.middleware import Middleware
from abi_coach.domain.common.result import Result


class ExecutionPipeline:
    """Manages an ordered chain of middlewares wrapping a target command handler."""

    def __init__(self, middlewares: Optional[List[Middleware]] = None):
        self._middlewares: List[Middleware] = list(middlewares) if middlewares else []

    def add_middleware(self, middleware: Middleware) -> "ExecutionPipeline":
        """Add middleware to the pipeline chain."""
        self._middlewares.append(middleware)
        return self

    def execute(
        self,
        command: Any,
        handler: Callable[[Any], Result],
    ) -> Result:
        """Execute command through all registered middlewares down to target handler."""
        # Build the onion / Russian doll chain from inside out
        current_chain: Callable[[Any], Result] = handler

        for mw in reversed(self._middlewares):
            next_step = current_chain

            def make_step(m: Middleware, n: Callable[[Any], Result]):
                return lambda cmd: m.handle(cmd, n)

            current_chain = make_step(mw, next_step)

        return current_chain(command)
