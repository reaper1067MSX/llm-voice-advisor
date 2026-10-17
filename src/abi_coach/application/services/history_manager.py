"""Thread-safe conversation history manager with rolling window pruning."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Iterator, List


@dataclass
class Turn:
    """Single turn in a conversation."""

    role: str
    text: str


class ConversationHistoryManager:
    """Manages rolling conversation history window in a thread-safe manner."""

    def __init__(self, max_turns: int = 50) -> None:
        self._max_turns = max_turns
        self._turns: List[Turn] = []
        self._lock = threading.Lock()

    @property
    def turns(self) -> List[Turn]:
        with self._lock:
            return list(self._turns)

    def append(self, turn: Turn) -> None:
        """Add turn and prune to rolling window."""
        with self._lock:
            self._turns.append(turn)
            if len(self._turns) > self._max_turns:
                self._turns = self._turns[-self._max_turns:]

    def add_turn(self, role: str, text: str) -> None:
        """Convenience method to append a turn."""
        self.append(Turn(role=role, text=text))

    def add_user_coach(self, user_prompt: str, coach_response: str) -> None:
        """Add a paired user query and coach response turn."""
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
