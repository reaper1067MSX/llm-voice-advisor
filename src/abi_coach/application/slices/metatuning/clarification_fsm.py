"""Clarification Finite State Machine with 60s TTL for Meta-Tuning (<100 LOC)."""

import threading
import time
from typing import Optional, Tuple

from abi_coach.domain.entities.metatuning_records import (
    CANCELLATION_PHRASES,
    CONFIRMATION_RULES,
    ClarificationResolution,
    ClarificationState,
    is_cancellation_phrase,
)

CLARIFICATION_TTL_SEC: float = 60.0


class ClarificationFSM:
    """Thread-safe finite state machine managing clarification transitions and TTL (<100 LOC)."""

    def __init__(self, ttl_sec: float = CLARIFICATION_TTL_SEC) -> None:
        self.ttl_sec = ttl_sec
        self.pending: Optional[ClarificationState] = None
        self._lock = threading.RLock()

    @property
    def has_pending(self) -> bool:
        with self._lock:
            return self.pending is not None

    def start(self, prompt: str, context_id: str = "generic", category: str = "general") -> ClarificationState:
        with self._lock:
            self.pending = ClarificationState(prompt, context_id, category, time.time())
            return self.pending

    def start_clarification(self, prompt: str, context_id: str = "generic", category: str = "general") -> ClarificationState:
        return self.start(prompt, context_id, category)

    def is_expired(self, now: Optional[float] = None, auto_reset: bool = False) -> bool:
        with self._lock:
            if not self.pending:
                return False
            created = getattr(self.pending, "created_at", None) or getattr(self.pending, "timestamp", None)
            if created is None and isinstance(self.pending, dict):
                created = self.pending.get("created_at") or self.pending.get("timestamp")
            expired = ((time.time() if now is None else now) - float(created)) > self.ttl_sec if created is not None else False
            if expired and auto_reset:
                self.pending = None
            return expired

    def is_cancellation(self, text: str) -> bool:
        return is_cancellation_phrase(text)

    def resolve(self, text: str) -> Tuple[Optional[ClarificationState], ClarificationResolution]:
        with self._lock:
            state = self.pending
            self.pending = None
            category = (state.category or "general") if state else "general"
            for kws, title, slug, what, learned in CONFIRMATION_RULES:
                if any(k in text.lower() for k in kws):
                    return state, ClarificationResolution(title, slug, what, learned)
            return state, ClarificationResolution(
                f"Regla Personalizada: {category.title()}",
                f"{category}_{int(time.time())}",
                f"Regla establecida: {text.strip()}",
                "Comportamiento calibrado a petición del jugador.",
            )

    def reset(self) -> None:
        with self._lock:
            self.pending = None

    def clear(self) -> None:
        self.reset()


__all__ = [
    "CANCELLATION_PHRASES",
    "CLARIFICATION_TTL_SEC",
    "CONFIRMATION_RULES",
    "ClarificationFSM",
    "ClarificationResolution",
    "ClarificationState",
    "is_cancellation_phrase",
]
