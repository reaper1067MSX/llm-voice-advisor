"""Companion Memory Outbound Port (Domain Layer)."""

from typing import List, Optional, Protocol
from abi_coach.domain.common.errors import StorageError
from abi_coach.domain.common.result import Result
from abi_coach.domain.common.value_objects import TopicKey
from abi_coach.domain.entities.player_memory import PlayerMemory


class MemoryRepositoryPort(Protocol):
    """Port for persisting and retrieving player memories and preferences."""

    def save_memory(self, memory: PlayerMemory) -> Result[None, StorageError]:
        """Save or update a player memory."""
        ...

    def get_memory(self, topic_key: TopicKey) -> Result[Optional[PlayerMemory], StorageError]:
        """Retrieve memory by topic key."""
        ...

    def get_active_profile(
        self,
        game: str = "generic",
        limit: int = 6,
    ) -> Result[List[PlayerMemory], StorageError]:
        """Get pinned and top-priority memories for context prompt building."""
        ...

    def search_memories(
        self,
        query: str,
        game: str = "generic",
        limit: int = 5,
    ) -> Result[List[PlayerMemory], StorageError]:
        """Search player memories by keywords."""
        ...
