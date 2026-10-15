"""Unit tests for ArchetypeManager, dynamic entities, and Engram observations."""

from pathlib import Path
import pytest

from abi_coach.archetypes import ArchetypeManager, DynamicEntity, EngramObservation
from abi_coach.db import DatabaseManager


def test_archetype_manager_default_seeding(tmp_path: Path):
    db_file = tmp_path / "test_arch.sqlite3"
    db = DatabaseManager(str(db_file))
    mgr = ArchetypeManager(db)

    archetypes = mgr.list_archetypes()
    arch_ids = {a.archetype_id for a in archetypes}

    assert "extraction_shooter" in arch_ids
    assert "survival_craft" in arch_ids
    assert "rpg_mmo" in arch_ids
    assert "general_companion" in arch_ids

    shooter = mgr.get_archetype("extraction_shooter")
    assert shooter is not None
    assert "penetration" in shooter.schema_template["facets"]


def test_archetype_manager_create_context_and_entities(tmp_path: Path):
    db_file = tmp_path / "test_ctx.sqlite3"
    db = DatabaseManager(str(db_file))
    mgr = ArchetypeManager(db)

    # 1. Create a dynamic context for Once Human
    ctx = mgr.create_context(
        context_id="once_human",
        archetype_id="survival_craft",
        display_name="Once Human (Temporada 1)",
        config={"silo_difficulty": "master"},
    )
    assert ctx.context_id == "once_human"
    assert ctx.is_active is True

    # 2. Add an entity with flexible facets (no ballistic columns!)
    silo_entity = DynamicEntity(
        context_id="once_human",
        category="silo",
        entity_key="silo:theta:hard",
        title="Silo Theta (Mod Shrapnel)",
        facets={
            "silo_name": "Theta",
            "recommended_level": 50,
            "elemental_type": "Fire / Shrapnel",
            "best_weapon": "AWS .338 Bingo",
            "key_boss": "Gorgon Core",
        },
        summary="Silo Theta en dificultad Hard. El mejor punto para farmear mods de Shrapnel de sufijo Violencia.",
        confidence=0.98,
        source="wiki_verified",
    )
    row_id = mgr.upsert_entity(silo_entity)
    assert row_id is not None

    # 3. Retrieve entity
    retrieved = mgr.get_entity("silo:theta:hard")
    assert retrieved is not None
    assert retrieved["facets"]["silo_name"] == "Theta"
    assert retrieved["facets"]["elemental_type"] == "Fire / Shrapnel"

    # 4. Search entity via FTS5
    search_res = mgr.search_entities("Shrapnel", context_id="once_human")
    assert len(search_res) >= 1
    assert "Silo Theta" in search_res[0]["title"]
    assert search_res[0]["facets"]["recommended_level"] == 50


def test_archetype_manager_engram_observations(tmp_path: Path):
    db_file = tmp_path / "test_engram.sqlite3"
    db = DatabaseManager(str(db_file))
    mgr = ArchetypeManager(db)

    # 1. Save an Engram-compliant observation
    obs = EngramObservation(
        context_id="once_human",
        scope="project",
        topic_key="builds/shrapnel_primary",
        observation_type="preference",
        title="Build Shrapnel Preferida",
        content="**What**: Usa rifle SOCR con 4 piezas Falcon.\n**Why**: Maximizar daño crítico en puntos débiles.\n**Where**: Ranura de arma primaria.",
        pinned=True,
    )
    mgr.save_engram_observation(obs)

    # 2. Retrieve observations
    obs_list = mgr.get_engram_observations("once_human")
    assert len(obs_list) == 1
    assert obs_list[0]["title"] == "Build Shrapnel Preferida"
    assert obs_list[0]["pinned"] == 1

    # 3. Format for prompt
    prompt_block = mgr.format_profile_for_prompt("once_human")
    assert "MEMORIA PERSISTENTE ENGRAM" in prompt_block
    assert "ONCE_HUMAN" in prompt_block
    assert "Build Shrapnel Preferida" in prompt_block
    assert "⭐ " in prompt_block
