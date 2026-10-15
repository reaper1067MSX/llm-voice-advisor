"""Companion Memory Vertical Slice (Application Layer)."""

from dataclasses import dataclass
from typing import List, Optional

from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result
from abi_coach.domain.common.value_objects import TopicKey
from abi_coach.domain.entities.player_memory import PlayerMemory
from abi_coach.domain.ports.memory_port import MemoryRepositoryPort


@dataclass(frozen=True)
class SaveMemoryCommand:
    topic_key: TopicKey
    title: str
    content: str
    memory_type: str = "preference"
    pinned: bool = False


@dataclass(frozen=True)
class GetActiveProfileQuery:
    game: str = "generic"
    limit: int = 6


class CompanionMemoryHandler:
    """Use Case Handler for player preferences and long-term recall."""

    def __init__(self, memory_port: MemoryRepositoryPort):
        self.memory_port = memory_port

    def handle_save(self, command: SaveMemoryCommand) -> Result[None, DomainError]:
        mem = PlayerMemory(
            topic_key=command.topic_key,
            title=command.title,
            content=command.content,
            memory_type=command.memory_type,
            pinned=command.pinned,
        )
        return self.memory_port.save_memory(mem)

    def handle_query_profile(self, query: GetActiveProfileQuery) -> Result[List[PlayerMemory], DomainError]:
        return self.memory_port.get_active_profile(game=query.game, limit=query.limit)
