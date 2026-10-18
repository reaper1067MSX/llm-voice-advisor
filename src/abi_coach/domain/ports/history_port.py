"""Port defining conversation history operations."""

from __future__ import annotations

from typing import Any, List, Protocol, runtime_checkable


@runtime_checkable
class ConversationHistoryPort(Protocol):
    """Port defining the contract for conversation history storage and retrieval."""

    def record_turn(self, role: str, text: str) -> None:
        """Record a single conversation turn."""
        ...

    def add_user_coach(self, user_prompt: str, coach_response: str) -> None:
        """Record a paired user query and coach response exchange."""
        ...

    def get_history_slice(self, max_turns: int = 5) -> List[str]:
        """Retrieve recent exchanges formatted as lines for context."""
        ...

    def clear(self) -> None:
        """Clear all stored turns."""
        ...
