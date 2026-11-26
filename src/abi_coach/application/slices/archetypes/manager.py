"""Dynamic Archetype-based Topic & Entity Manager (Archetypes Slice)."""

from typing import Any, Optional

from abi_coach.application.slices.archetypes.prompt_formatter import ArchetypePromptFormatter
from abi_coach.domain.entities.archetype_entities import (
    SPANISH_FTS_STOPWORDS,
    ArchetypeDefinition,
    DynamicEntity,
    EngramObservation,
    TopicContext,
)
from abi_coach.domain.ports.archetype_repository_port import ArchetypeRepositoryPort
from abi_coach.infrastructure.adapters.storage.sqlite_archetype_repository import (
    SqliteArchetypeRepository,
    sanitize_fts_query,
)


class ArchetypeManager:
    """Manages archetype blueprints, topic contexts, dynamic entities, and Engram observations."""

    def __init__(
        self,
        db: Any,
        repository: Optional[ArchetypeRepositoryPort] = None,
        formatter: Optional[ArchetypePromptFormatter] = None,
    ) -> None:
        self.db = db
        if repository is not None:
            self._repo: ArchetypeRepositoryPort = repository
        elif isinstance(db, ArchetypeRepositoryPort):
            self._repo = db
        else:
            self._repo = SqliteArchetypeRepository(db)
        self._formatter = formatter or ArchetypePromptFormatter()

    def list_archetypes(self) -> list[ArchetypeDefinition]:
        """List all available foundational domain archetypes."""
        return self._repo.list_archetypes()

    def get_archetype(self, archetype_id: str) -> Optional[ArchetypeDefinition]:
        """Retrieve an archetype by its unique ID."""
        return self._repo.get_archetype(archetype_id)

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
        return self._repo.create_context(
            context_id=context_id,
            archetype_id=archetype_id,
            display_name=display_name,
            config=config,
            version=version,
            activate=activate,
        )

    def get_context(self, context_id: str) -> Optional[TopicContext]:
        """Retrieve an active or registered topic context by ID."""
        return self._repo.get_context(context_id)

    def upsert_entity(self, entity: DynamicEntity) -> int:
        """Upsert a dynamic entity with JSON facets and FTS5 indexing."""
        return self._repo.upsert_entity(entity)

    def get_entity(self, entity_key: str) -> Optional[dict[str, Any]]:
        """Retrieve an entity by unique entity_key."""
        return self._repo.get_entity(entity_key)

    def _sanitize_fts_query(self, raw_query: str) -> str:
        """Sanitize user query into an FTS5 prefix OR clause."""
        return sanitize_fts_query(raw_query)

    def search_entities(self, query: str, context_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search over dynamic entities within context."""
        return self._repo.search_entities(query=query, context_id=context_id, limit=limit)

    def save_engram_observation(self, obs: EngramObservation) -> int:
        """Save observation conforming to gentle-ai Engram specification."""
        return self._repo.save_engram_observation(obs)

    def get_engram_observations(self, context_id: str, limit: int = 6) -> list[dict[str, Any]]:
        """Retrieve top active observations for prompt enrichment."""
        return self._repo.get_engram_observations(context_id=context_id, limit=limit)

    def format_profile_for_prompt(self, context_id: str, limit: int = 6) -> str:
        """Format active Engram observations into a prompt injection block."""
        obs = self.get_engram_observations(context_id=context_id, limit=limit)
        return self._formatter.format_profile_for_prompt(context_id=context_id, observations=obs)

    def format_rag_for_prompt(self, query: str, context_id: str, limit: int = 2) -> str:
        """Format matching dynamic entities into a verification block for the LLM prompt."""
        matches = self.search_entities(query=query, context_id=context_id, limit=limit)
        return self._formatter.format_rag_for_prompt(context_id=context_id, matches=matches)


__all__ = [
    "SPANISH_FTS_STOPWORDS",
    "ArchetypeDefinition",
    "ArchetypeManager",
    "DynamicEntity",
    "EngramObservation",
    "TopicContext",
]
