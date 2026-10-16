"""Unit tests for ArchetypeScaffolder and autonomous topic bootstrapping."""

from pathlib import Path
import pytest

from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager


def test_archetype_detection_heuristic(tmp_path: Path):
    db_file = tmp_path / "test_scaff_detect.sqlite3"
    db = DatabaseManager(str(db_file))
    scaffolder = ArchetypeScaffolder(db)

    assert scaffolder.detect_archetype("Arena Breakout") == "extraction_shooter"
    assert scaffolder.detect_archetype("Escape from Tarkov") == "extraction_shooter"
    assert scaffolder.detect_archetype("Once Human") == "survival_craft"
    assert scaffolder.detect_archetype("Rust") == "survival_craft"
    assert scaffolder.detect_archetype("Elden Ring") == "rpg_mmo"
    assert scaffolder.detect_archetype("World of Warcraft") == "rpg_mmo"
    assert scaffolder.detect_archetype("Chess 3D") == "general_companion"


def test_bootstrap_context_zero_seeder(tmp_path: Path):
    db_file = tmp_path / "test_bootstrap.sqlite3"
    db = DatabaseManager(str(db_file))
    scaffolder = ArchetypeScaffolder(db)

    # Bootstrap Once Human from scratch without any seed file!
    ctx = scaffolder.bootstrap_context(
        context_id="once_human",
        display_name="Once Human",
        initial_config={"server": "NA-01"},
    )

    assert ctx.context_id == "once_human"
    assert ctx.archetype_id == "survival_craft"
    assert ctx.is_active is True

    # Verify Engram observations were auto-scaffolded
    observations = scaffolder.mgr.get_engram_observations("once_human")
    assert len(observations) >= 2
    keys = {o["topic_key"] for o in observations}
    assert "once_human/player/profile" in keys
    assert "once_human/rules/tactical" in keys


def test_auto_ingest_fact_without_files(tmp_path: Path):
    db_file = tmp_path / "test_auto_ingest.sqlite3"
    db = DatabaseManager(str(db_file))
    scaffolder = ArchetypeScaffolder(db)

    # Ingest a freshly observed mod in Once Human
    entity = scaffolder.auto_ingest_fact(
        context_id="once_human",
        category="weapon_mod",
        title="Mod Violencia Shrapnel",
        summary="Mod dorado legendario. Aumenta daño crítico un 18%.",
        facets={"tier": "legendary", "crit_dmg_bonus": 18, "slot": "weapon"},
        source="vision_screen_ocr",
    )

    assert entity.entity_key.startswith("weapon_mod:once_human:")
    assert entity.title == "Mod Violencia Shrapnel"

    # Search in FTS5
    results = scaffolder.mgr.search_entities("Shrapnel", context_id="once_human")
    assert len(results) == 1
    assert results[0]["title"] == "Mod Violencia Shrapnel"
    assert results[0]["facets"]["crit_dmg_bonus"] == 18
