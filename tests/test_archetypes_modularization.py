"""Isolated unit tests for Archetypes slice modularization (Etapa 5)."""

from pathlib import Path
from typing import Any, Optional

import pytest

from abi_coach.application.slices.archetypes.manager import ArchetypeManager
from abi_coach.application.slices.archetypes.prompt_formatter import ArchetypePromptFormatter
from abi_coach.domain.entities.archetype_entities import (
    SPANISH_FTS_STOPWORDS,
    ArchetypeDefinition,
    DynamicEntity,
    EngramObservation,
    TopicContext,
)
from abi_coach.domain.ports.archetype_repository_port import ArchetypeRepositoryPort
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.adapters.storage.sqlite_archetype_repository import (
    SqliteArchetypeRepository,
    sanitize_fts_query,
)


class InMemoryArchetypeRepository:
    """In-memory fake implementing ArchetypeRepositoryPort without SQLite."""

    def __init__(self) -> None:
        self.archetypes: dict[str, ArchetypeDefinition] = {
            "survival_craft": ArchetypeDefinition(
                archetype_id="survival_craft",
                display_name="Survival Craft",
                schema_template={"categories": ["silo"], "facets": ["tier"]},
                default_system_prompt="Prompt de supervivencia.",
            )
        }
        self.contexts: dict[str, TopicContext] = {}
        self.entities: dict[str, dict[str, Any]] = {}
        self.observations: list[dict[str, Any]] = []

    def list_archetypes(self) -> list[ArchetypeDefinition]:
        return list(self.archetypes.values())

    def get_archetype(self, archetype_id: str) -> Optional[ArchetypeDefinition]:
        return self.archetypes.get(archetype_id.strip().lower())

    def create_context(
        self,
        context_id: str,
        archetype_id: str,
        display_name: str,
        config: Optional[dict[str, Any]] = None,
        version: str = "1.0",
        activate: bool = True,
    ) -> TopicContext:
        cid = context_id.strip().lower()
        ctx = TopicContext(
            context_id=cid,
            archetype_id=archetype_id,
            display_name=display_name,
            current_version=version,
            config=config or {},
            is_active=activate,
        )
        self.contexts[cid] = ctx
        return ctx

    def get_context(self, context_id: str) -> Optional[TopicContext]:
        return self.contexts.get(context_id.strip().lower())

    def upsert_entity(self, entity: DynamicEntity) -> int:
        self.entities[entity.entity_key] = {
            "id": len(self.entities) + 1,
            "context_id": entity.context_id,
            "category": entity.category,
            "entity_key": entity.entity_key,
            "title": entity.title,
            "facets": entity.facets,
            "summary": entity.summary,
            "confidence": entity.confidence,
            "source": entity.source,
        }
        return len(self.entities)

    def get_entity(self, entity_key: str) -> Optional[dict[str, Any]]:
        return self.entities.get(entity_key)

    def search_entities(self, query: str, context_id: str, limit: int = 5) -> list[dict[str, Any]]:
        q_lower = query.lower()
        matches = [
            item
            for item in self.entities.values()
            if item["context_id"] == context_id and q_lower in item["title"].lower()
        ]
        return matches[:limit]

    def save_engram_observation(self, obs: EngramObservation) -> int:
        self.observations.append(
            {
                "id": len(self.observations) + 1,
                "context_id": obs.context_id,
                "scope": obs.scope,
                "topic_key": obs.topic_key,
                "observation_type": obs.observation_type,
                "title": obs.title,
                "content": obs.content,
                "pinned": 1 if obs.pinned else 0,
            }
        )
        return len(self.observations)

    def get_engram_observations(self, context_id: str, limit: int = 6) -> list[dict[str, Any]]:
        return [o for o in self.observations if o["context_id"] == context_id][:limit]


def test_in_memory_fake_satisfies_archetype_repository_port() -> None:
    """Verify ArchetypeManager works purely over ArchetypeRepositoryPort without SQLite."""
    fake_repo = InMemoryArchetypeRepository()
    assert isinstance(fake_repo, ArchetypeRepositoryPort)

    mgr = ArchetypeManager(db=fake_repo)
    assert len(mgr.list_archetypes()) == 1
    assert mgr.get_archetype("survival_craft") is not None

    ctx = mgr.create_context("once_human", "survival_craft", "Once Human")
    assert mgr.get_context("once_human") == ctx

    entity = DynamicEntity(
        context_id="once_human",
        category="silo",
        entity_key="silo:alpha",
        title="Silo Alpha",
        facets={"tier": "hard"},
        summary="Resumen Silo Alpha",
        confidence=0.95,
    )
    assert mgr.upsert_entity(entity) == 1
    assert mgr.get_entity("silo:alpha") is not None

    rag_block = mgr.format_rag_for_prompt("Alpha", context_id="once_human")
    assert "Silo Alpha" in rag_block
    assert "95%" in rag_block

    obs = EngramObservation(
        context_id="once_human",
        scope="project",
        topic_key="once_human/rules",
        observation_type="rule",
        title="Regla de Silo",
        content="Usar munición de fuego.",
        pinned=True,
    )
    mgr.save_engram_observation(obs)
    profile_block = mgr.format_profile_for_prompt("once_human")
    assert "⭐ [RULE] Regla de Silo: Usar munición de fuego." in profile_block


@pytest.mark.parametrize(
    ("raw_query", "expected_fts"),
    [
        ("de la el en que", ""),
        ("M80 de 7.62", '"M80"* OR "7.62"*'),
        ("Silo Theta con Shrapnel", '"Silo"* OR "Theta"* OR "Shrapnel"*'),
    ],
)
def test_sanitize_fts_query_filters_spanish_stopwords(
    raw_query: str,
    expected_fts: str,
) -> None:
    assert "de" in SPANISH_FTS_STOPWORDS
    assert sanitize_fts_query(raw_query) == expected_fts


def test_prompt_formatter_handles_empty_and_json_fallback() -> None:
    formatter = ArchetypePromptFormatter()
    assert formatter.format_profile_for_prompt("abi", []) == ""
    assert formatter.format_rag_for_prompt("abi", []) == ""

    block = formatter.format_rag_for_prompt(
        "abi",
        [
            {
                "category": "ammo",
                "title": "7.62 M80",
                "summary": "Tier 4",
                "confidence": 0.9,
                "facets_json": '{"penetration": 44}',
            }
        ],
    )
    assert "[AMMO] 7.62 M80 (Confiabilidad: 90%)" in block
    assert '"penetration": 44' in block


@pytest.mark.integration
def test_sqlite_archetype_repository_fts_and_like_fallback(tmp_path: Path) -> None:
    db = DatabaseManager(str(tmp_path / "test_repo.sqlite3"))
    repo = SqliteArchetypeRepository(db)
    repo.create_context("abi", "extraction_shooter", "ABI")
    repo.upsert_entity(
        DynamicEntity(
            context_id="abi",
            category="ammo",
            entity_key="ammo:m80",
            title="M80 7.62x51",
            facets={"tier": 4},
            summary="Munición estándar T4",
        )
    )
    results = repo.search_entities("M80", context_id="abi")
    assert len(results) == 1
    assert results[0]["facets"]["tier"] == 4
