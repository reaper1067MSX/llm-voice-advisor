"""Structured Logging Adapter for LLM Game Advisor.

Provides structured JSON Lines logging for machine-parsable exception diagnostics
and formatted text logging for real-time observability without impacting game performance.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import traceback
from typing import Any, Dict, Optional


@dataclass
class ExceptionDetail:
    type: str
    message: str
    traceback: str


@dataclass
class StructuredLogEntry:
    timestamp: str
    level: str
    component: str
    action: str
    agent: str = "core"
    latency_ms: float = 0.0
    game_context: str = "generic"
    user_prompt_snippet: Optional[str] = None
    exception: Optional[ExceptionDetail] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        data = asdict(self)
        # Prune None fields for clean JSON
        if data["exception"] is None:
            del data["exception"]
        if data["user_prompt_snippet"] is None:
            del data["user_prompt_snippet"]
        if not data["extra"]:
            del data["extra"]
        return json.dumps(data, ensure_ascii=False)


class StructuredLogger:
    """Centralized diagnostic and event logger for multi-agent game advisor components."""

    _instance: Optional["StructuredLogger"] = None

    def __init__(self, logs_dir: Optional[Path] = None):
        self.logs_dir = logs_dir or Path("logs")
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.exceptions_file = self.logs_dir / "exceptions.jsonl"
        self.text_log_file = self.logs_dir / "advisor.log"

        # Initialize standard rotating logger for plain text
        self._logger = logging.getLogger("abi_coach")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = RotatingFileHandler(
                str(self.text_log_file),
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
                encoding="utf-8",
            )
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    @classmethod
    def get_instance(cls, logs_dir: Optional[Path] = None) -> "StructuredLogger":
        if cls._instance is None:
            cls._instance = cls(logs_dir=logs_dir)
        return cls._instance

    def log_event(
        self,
        component: str,
        action: str,
        agent: str = "core",
        level: str = "INFO",
        latency_ms: float = 0.0,
        game_context: str = "generic",
        user_prompt: str = "",
        **extra: Any,
    ) -> None:
        """Record a structured operational event."""
        timestamp = datetime.now(timezone.utc).isoformat()
        snippet = user_prompt[:80] if user_prompt else None

        entry = StructuredLogEntry(
            timestamp=timestamp,
            level=level.upper(),
            component=component,
            action=action,
            agent=agent,
            latency_ms=round(latency_ms, 2),
            game_context=game_context,
            user_prompt_snippet=snippet,
            extra=extra,
        )

        msg = f"[{component}:{agent}] {action} (lat={latency_ms:.1f}ms)"
        if level.upper() == "DEBUG":
            self._logger.debug(msg)
        elif level.upper() == "WARNING":
            self._logger.warning(msg)
        elif level.upper() == "ERROR":
            self._logger.error(msg)
        else:
            self._logger.info(msg)

    def log_exception(
        self,
        component: str,
        action: str,
        exc: BaseException,
        agent: str = "core",
        game_context: str = "generic",
        user_prompt: str = "",
        **extra: Any,
    ) -> None:
        """Atomically record an unhandled or caught exception into exceptions.jsonl and text log."""
        timestamp = datetime.now(timezone.utc).isoformat()
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        entry = StructuredLogEntry(
            timestamp=timestamp,
            level="ERROR",
            component=component,
            action=action,
            agent=agent,
            game_context=game_context,
            user_prompt_snippet=user_prompt[:120] if user_prompt else None,
            exception=ExceptionDetail(
                type=type(exc).__name__,
                message=str(exc),
                traceback=tb_str,
            ),
            extra=extra,
        )

        # Write to JSON Lines for machine diagnostics
        try:
            with open(self.exceptions_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception:
            pass

        # Write to standard log file
        self._logger.error(
            f"EXCEPTION in [{component}:{agent}] during {action}: {type(exc).__name__}: {exc}\n{tb_str}"
        )


# Global helper functions for zero-ceremony logging
_GLOBAL_LOGGER = StructuredLogger.get_instance()


def log_event(component: str, action: str, **kwargs: Any) -> None:
    _GLOBAL_LOGGER.log_event(component=component, action=action, **kwargs)


def log_exception(component: str, action: str, exc: BaseException, **kwargs: Any) -> None:
    _GLOBAL_LOGGER.log_exception(component=component, action=action, exc=exc, **kwargs)
