"""Thread-safe conversation history manager implementing ConversationHistoryPort."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Iterator, List

from abi_coach.domain.ports.history_port import ConversationHistoryPort


@dataclass(frozen=True)
class Turn:
    """Immutable single turn in a conversation."""

    role: str
    text: str


class ConversationHistoryManager(ConversationHistoryPort):
    """Thread-safe rolling conversation history manager implementing ConversationHistoryPort."""

    def __init__(self, max_turns: int = 50) -> None:
        self._max_turns = max_turns
        self._turns: List[Turn] = []
        self._lock = threading.Lock()

    @property
    def turns(self) -> List[Turn]:
        with self._lock:
            return list(self._turns)

    def record_turn(self, role: str, text: str) -> None:
        """Record a single turn and prune to rolling window."""
        with self._lock:
            self._turns.append(Turn(role=role, text=text))
            if len(self._turns) > self._max_turns:
                self._turns = self._turns[-self._max_turns:]

    def add_turn(self, role: str, text: str) -> None:
        """Convenience alias for record_turn."""
        self.record_turn(role, text)

    def add_user_coach(self, user_prompt: str, coach_response: str) -> None:
        """Record an atomic paired user query and coach response."""
        with self._lock:
            self._turns.append(Turn(role="user", text=user_prompt))
            self._turns.append(Turn(role="coach", text=coach_response))
            if len(self._turns) > self._max_turns:
                self._turns = self._turns[-self._max_turns:]

    def get_history_slice(self, max_turns: int = 5) -> List[str]:
        """Format last max_turns exchanges (user+coach) as uppercase role lines for LLM context."""
        with self._lock:
            mt = max(0, max_turns)
            if mt == 0:
                return []
            slice_turns = self._turns[-(mt * 2):]
            return [f"{t.role.upper()}: {t.text}" for t in slice_turns]

    def clear(self) -> None:
        """Clear all conversation history."""
        with self._lock:
            self._turns.clear()

    def __iter__(self) -> Iterator[Turn]:
        with self._lock:
            return iter(list(self._turns))

    def __len__(self) -> int:
        with self._lock:
            return len(self._turns)

    def __getitem__(self, index: int) -> Turn:
        with self._lock:
            return self._turns[index]

    def __bool__(self) -> bool:
        return True
