"""SQLite Companion Memory Repository implementing MemoryRepositoryPort."""

from typing import List, Optional

from abi_coach.domain.common.errors import StorageError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.common.value_objects import TopicKey
from abi_coach.domain.entities.player_memory import PlayerMemory
from abi_coach.domain.ports.memory_port import MemoryRepositoryPort
from abi_coach.application.slices.companion_memory.memory import CompanionMemory, MemoryItem


class SqliteMemoryRepository(MemoryRepositoryPort):
    """Hexagonal Adapter for player memory persistence over SQLite."""

    def __init__(self, memory: CompanionMemory):
        self.memory = memory

    def save_memory(self, memory: PlayerMemory) -> Result[None, StorageError]:
        try:
            item = MemoryItem(
                game=memory.topic_key.game,
                topic=memory.topic_key.topic,
                feature=memory.topic_key.facet,
                topic_key=str(memory.topic_key),
                memory_type=memory.memory_type,
                title=memory.title,
                content=memory.content,
                pinned=memory.pinned,
            )
            self.memory.save_memory(item)
            return ok(None)
        except Exception as e:
            return fail(
                StorageError(
                    code="MEMORY_SAVE_ERROR",
                    message=f"Error al guardar memoria {memory.topic_key}: {e}",
                    operation="save_memory",
                )
            )

    def get_memory(self, topic_key: TopicKey) -> Result[Optional[PlayerMemory], StorageError]:
        try:
            raw = self.memory.get_memory(str(topic_key))
            if not raw:
                return ok(None)

            mem = PlayerMemory(
                topic_key=TopicKey(raw["topic_key"]),
                title=raw["title"],
                content=raw["content"],
                memory_type=raw.get("memory_type", "preference"),
                pinned=bool(raw.get("pinned", 0)),
                access_count=raw.get("access_count", 0),
            )
            return ok(mem)
        except Exception as e:
            return fail(
                StorageError(
                    code="MEMORY_GET_ERROR",
                    message=f"Error al obtener memoria {topic_key}: {e}",
                    operation="get_memory",
                )
            )

    def get_active_profile(
        self,
        game: str = "generic",
        limit: int = 6,
    ) -> Result[List[PlayerMemory], StorageError]:
        try:
            raw_list = self.memory.get_active_profile(game=game, limit=limit)
            results: List[PlayerMemory] = []
            for r in raw_list:
                results.append(
                    PlayerMemory(
                        topic_key=TopicKey(r["topic_key"]),
                        title=r["title"],
                        content=r["content"],
                        memory_type=r.get("memory_type", "preference"),
                        pinned=bool(r.get("pinned", 0)),
                        access_count=r.get("access_count", 0),
                    )
                )
            return ok(results)
        except Exception as e:
            return fail(
                StorageError(
                    code="MEMORY_PROFILE_ERROR",
                    message=f"Error al obtener perfil activo de {game}: {e}",
                    operation="get_active_profile",
                )
            )

    def search_memories(
        self,
        query: str,
        game: str = "generic",
        limit: int = 5,
    ) -> Result[List[PlayerMemory], StorageError]:
        try:
            raw_list = self.memory.search_memories(query=query, game=game, limit=limit)
            results: List[PlayerMemory] = []
            for r in raw_list:
                results.append(
                    PlayerMemory(
                        topic_key=TopicKey(r["topic_key"]),
                        title=r["title"],
                        content=r["content"],
                        memory_type=r.get("memory_type", "preference"),
                        pinned=bool(r.get("pinned", 0)),
                        access_count=r.get("access_count", 0),
                    )
                )
            return ok(results)
        except Exception as e:
            return fail(
                StorageError(
                    code="MEMORY_SEARCH_ERROR",
                    message=f"Error al buscar memorias con '{query}': {e}",
                    operation="search_memories",
                )
            )
