"""Unit tests for KnowledgeReconciler and self-healing discrepancy detection."""

from pathlib import Path
import pytest

from abi_coach.application.slices.tactical_rag.rag import KnowledgeRAG
from abi_coach.application.slices.tactical_rag.reconciler import KnowledgeReconciler
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager


def test_reconciler_new_discovery(tmp_path: Path):
    db_file = tmp_path / "test_reconciler.sqlite3"
    db = DatabaseManager(str(db_file))
    rag = KnowledgeRAG(db, default_game="abi")
    reconciler = KnowledgeReconciler(db, rag)

    diffs = reconciler.reconcile_entity(
        entity_key="item:new_experimental_key",
        observed_data={"durability": 100, "price": 85000},
        title="Llave Experimental",
        category="item",
        reason="player_correction",
    )

    assert len(diffs) == 1
    assert diffs[0].field_name == "entity_creation"
    assert diffs[0].reason == "player_correction"

    # Verify created entity in RAG
    entity = rag.get_entity("item:new_experimental_key")
    assert entity is not None
    assert entity["title"] == "Llave Experimental"

    # Verify changelog
    logs = reconciler.get_changelog("item:new_experimental_key")
    assert len(logs) == 1
    assert logs[0]["field_name"] == "entity_creation"


def test_reconciler_patch_stat_diff(tmp_path: Path):
    db_file = tmp_path / "test_patch_diff.sqlite3"
    db = DatabaseManager(str(db_file))
    rag = KnowledgeRAG(db, default_game="abi")
    reconciler = KnowledgeReconciler(db, rag)

    # M80 starts with penetration: 44
    m80_initial = rag.get_entity("ammo:7.62x51:m80")
    assert m80_initial is not None

    # Game patch updates penetration to 46 and damage to 78
    diffs = reconciler.reconcile_entity(
        entity_key="ammo:7.62x51:m80",
        observed_data={"penetration": 46, "damage": 78},
        reason="patch_sync",
        new_summary="Calibre 7.62x51mm. Tier 4, Penetración 46, Daño 78. Buffeada en Season 7.1.",
    )

    assert len(diffs) == 2
    field_names = {d.field_name for d in diffs}
    assert field_names == {"penetration", "damage"}

    # Verify notice format
    notice = reconciler.format_reconciliation_notice(diffs)
    assert "ACTUALIZACIÓN DE PARCHE" in notice
    assert "penetration cambió de 44 a 46" in notice

    # Verify updated stored entity
    m80_updated = rag.get_entity("ammo:7.62x51:m80")
    assert "Buffeada en Season 7.1" in m80_updated["summary"]
    assert '"penetration": 46' in m80_updated["data_json"]

    # Verify changelog records
    logs = reconciler.get_changelog("ammo:7.62x51:m80")
    assert len(logs) == 2


def test_reconciler_no_changes_is_noop(tmp_path: Path):
    db_file = tmp_path / "test_noop.sqlite3"
    db = DatabaseManager(str(db_file))
    rag = KnowledgeRAG(db, default_game="abi")
    reconciler = KnowledgeReconciler(db, rag)

    # Identical values
    diffs = reconciler.reconcile_entity(
        entity_key="ammo:7.62x51:m80",
        observed_data={"penetration": 44, "damage": 76},
        reason="vision_observed",
    )

    assert len(diffs) == 0
    logs = reconciler.get_changelog("ammo:7.62x51:m80")
    assert len(logs) == 0
