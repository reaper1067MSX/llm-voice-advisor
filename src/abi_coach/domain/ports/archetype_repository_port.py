"""Outbound repository port for dynamic archetypes, contexts, entities, and Engram observations."""

from typing import Any, Optional, Protocol, runtime_checkable

from abi_coach.domain.entities.archetype_entities import (
    ArchetypeDefinition,
    DynamicEntity,
    EngramObservation,
    TopicContext,
)


@runtime_checkable
class ArchetypeRepositoryPort(Protocol):
    """Port defining persistence operations for the Archetypes slice."""

    def list_archetypes(self) -> list[ArchetypeDefinition]:
        """List all available foundational domain archetypes."""
        ...

    def get_archetype(self, archetype_id: str) -> Optional[ArchetypeDefinition]:
        """Retrieve an archetype by its unique ID."""
        ...

    def create_context(
        self,
        context_id: str,
        archetype_id: str,
        display_name: str,
        config: Optional[dict[str, Any]] = None,
        version: str = "1.0",
        activate: bool = True,
    ) -> TopicContext:
        """Create or update a topic context linked to an archetype blueprint."""
        ...

    def get_context(self, context_id: str) -> Optional[TopicContext]:
        """Retrieve an active or registered topic context by ID."""
        ...

    def upsert_entity(self, entity: DynamicEntity) -> int:
        """Upsert a dynamic entity with JSON facets and FTS5 indexing."""
        ...

    def get_entity(self, entity_key: str) -> Optional[dict[str, Any]]:
        """Retrieve an entity by unique entity_key."""
        ...

    def search_entities(self, query: str, context_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search dynamic entities within a topic context."""
        ...

    def save_engram_observation(self, obs: EngramObservation) -> int:
        """Save an Engram-compliant observation."""
        ...

    def get_engram_observations(self, context_id: str, limit: int = 6) -> list[dict[str, Any]]:
        """Retrieve top active observations for prompt enrichment."""
        ...


__all__ = ["ArchetypeRepositoryPort"]
