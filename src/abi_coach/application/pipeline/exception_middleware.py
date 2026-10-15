"""Exception Handling Middleware (Application Layer).

Catches any unexpected system panics, unhandled exceptions, and fatal crashes,
converting them into a safe Failure(SystemUnexpectedError) with spoken fallback.
"""

from typing import Any, Callable, Optional
import logging
from abi_coach.domain.common.errors import SystemUnexpectedError
from abi_coach.domain.common.result import Failure, Result, fail

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware:
    """Interception barrier that guarantees no unhandled system exceptions escape."""

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        self.logger = logger_instance or logger

    def handle(self, command: Any, next_handler: Callable[[Any], Result]) -> Result:
        try:
            return next_handler(command)
        except Exception as exc:
            self.logger.error(
                "Unhandled system exception intercepted by pipeline barrier: %s",
                exc,
                exc_info=True,
            )
            err = SystemUnexpectedError(
                code="SYSTEM_UNEXPECTED_EXCEPTION",
                message=f"Fallo no controlado en el sistema: {exc.__class__.__name__}",
                technical_detail=str(exc),
            )
            return fail(err)
